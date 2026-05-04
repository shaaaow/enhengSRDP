"""仿真计算路由 — 完整流程：音频读取 → 延迟信号生成 → GCC-PHAT TDOA 估计 → Chan 氏定位"""

import math
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from models.schemas import (
    SimulationRequest,
    SimulationResponse,
    TDOAResult,
    LocalizationResult,
)
from services.audio_service import (
    read_wav,
    resolve_audio_path,
    generate_delayed_signals,
)
from algorithms.registry import get_tdoa_estimator, get_localizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulation", tags=["仿真计算"])


@router.post("/run", response_model=SimulationResponse)
async def run_simulation(req: SimulationRequest):
    """执行完整仿真计算"""
    try:
        audio_path = resolve_audio_path(req.audio_file)
    except FileNotFoundError:
        raise HTTPException(404, f"找不到音频文件: {req.audio_file}")

    try:
        source_audio, sample_rate = read_wav(audio_path)
    except Exception as e:
        raise HTTPException(400, f"读取音频失败: {e}")

    sensor_coords = [(s.x, s.y) for s in req.sensors]
    source_pos = (req.source.x, req.source.y)

    try:
        signal_paths = generate_delayed_signals(
            source_audio=source_audio,
            sample_rate=sample_rate,
            sensors=sensor_coords,
            source_pos=source_pos,
            sound_speed=req.sound_speed,
            snr_db=req.snr_db,
        )
    except Exception as e:
        raise HTTPException(500, f"生成延迟信号失败: {e}")

    # 计算理论 TDOA（几何精确值）
    sx, sy = source_pos
    distances = [math.sqrt((sx - x) ** 2 + (sy - y) ** 2) for x, y in sensor_coords]
    theoretical_tdoa = {}
    for (i, j), label in zip([(0, 1), (0, 2), (1, 2)], ["12", "13", "23"]):
        theoretical_tdoa[label] = (distances[i] - distances[j]) / req.sound_speed

    # GCC-PHAT TDOA 估计
    estimator = get_tdoa_estimator("gcc_phat")
    pairs = [(0, 1), (0, 2), (1, 2)]
    pair_labels = ["12", "13", "23"]
    tdoa_dict = {}
    peak_dict = {}

    for (i, j), label in zip(pairs, pair_labels):
        try:
            result = await estimator.estimate(
                ref_path=str(signal_paths[i]),
                target_path=str(signal_paths[j]),
                sample_rate=sample_rate,
            )
            tdoa_dict[label] = result["tdoa_sec"]
            peak_dict[label] = result.get("peak_value", 0.0)
        except Exception as e:
            logger.error("GCC-PHAT 对 %s 失败: %s", label, e)
            raise HTTPException(500, f"TDOA 估计失败 (传感器对 {label}): {e}")

    tdoa_result = TDOAResult(
        dt12=round(tdoa_dict["12"], 6),
        dt13=round(tdoa_dict["13"], 6),
        dt23=round(tdoa_dict["23"], 6),
        dt12_theoretical=round(theoretical_tdoa["12"], 6),
        dt13_theoretical=round(theoretical_tdoa["13"], 6),
        dt23_theoretical=round(theoretical_tdoa["23"], 6),
        gcc_peak_12=round(peak_dict["12"], 4),
        gcc_peak_13=round(peak_dict["13"], 4),
        gcc_peak_23=round(peak_dict["23"], 4),
    )

    localizer = get_localizer("chan")

    try:
        loc_result = localizer.localize(
            sensors=sensor_coords,
            tdoa_values=[tdoa_dict["12"], tdoa_dict["13"]],
            sound_speed=req.sound_speed,
        )
    except Exception as e:
        logger.error("Chan 氏定位失败: %s", e)
        raise HTTPException(500, f"定位解算失败: {e}")

    error_m = math.sqrt(
        (loc_result["x"] - req.source.x) ** 2
        + (loc_result["y"] - req.source.y) ** 2
    )

    loc_response = LocalizationResult(
        x=loc_result["x"],
        y=loc_result["y"],
        gdop=loc_result["gdop"],
        gdop_quality=loc_result["gdop_quality"],
        error_estimate_m=round(error_m, 4),
    )

    return SimulationResponse(
        success=True,
        message="仿真计算完成",
        tdoa=tdoa_result,
        localization=loc_response,
        snr_db=req.snr_db,
        timestamp=datetime.now(),
    )
