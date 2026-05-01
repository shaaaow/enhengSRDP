"""音频文件 I/O 与仿真延迟信号生成"""

import sys
import wave
import struct
import logging
from pathlib import Path

import numpy as np

from config import UPLOAD_DIR, PRESET_AUDIO_DIR, TEMP_DIR, PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT / "core" / "src"))
from noise_generator import add_awgn

logger = logging.getLogger(__name__)


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """手动解析 RIFF/WAV，支持 PCM 和 IEEE Float 格式

    @param path - .wav 文件路径
    @returns (单声道浮点信号, 采样率)
    """
    with open(path, "rb") as f:
        riff = f.read(12)
        if riff[:4] != b"RIFF" or riff[8:12] != b"WAVE":
            raise ValueError("不是有效的 WAV 文件")

        audio_fmt = 0
        n_channels = 0
        sample_rate = 0
        bits_per_sample = 0
        raw_data = b""

        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            chunk_id = chunk_header[:4]
            chunk_size = struct.unpack("<I", chunk_header[4:8])[0]

            if chunk_id == b"fmt ":
                fmt_data = f.read(chunk_size)
                audio_fmt = struct.unpack("<H", fmt_data[:2])[0]
                n_channels = struct.unpack("<H", fmt_data[2:4])[0]
                sample_rate = struct.unpack("<I", fmt_data[4:8])[0]
                bits_per_sample = struct.unpack("<H", fmt_data[14:16])[0]
            elif chunk_id == b"data":
                raw_data = f.read(chunk_size)
            else:
                f.seek(chunk_size, 1)

    if not raw_data:
        raise ValueError("WAV 文件中未找到 data 块")

    if audio_fmt == 3 and bits_per_sample == 32:
        n_samples = len(raw_data) // 4
        samples = np.frombuffer(raw_data, dtype=np.float32).copy()
    elif audio_fmt == 1 and bits_per_sample == 16:
        n_samples = len(raw_data) // 2
        samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    elif audio_fmt == 1 and bits_per_sample == 32:
        n_samples = len(raw_data) // 4
        samples = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif audio_fmt == 1 and bits_per_sample == 24:
        n_samples = len(raw_data) // 3
        padded = b"".join(b"\x00" + raw_data[i:i+3] for i in range(0, len(raw_data), 3))
        samples = np.frombuffer(padded, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"不支持的 WAV 格式: format={audio_fmt}, bits={bits_per_sample}")

    if n_channels > 1:
        samples = samples[::n_channels]

    return samples, sample_rate


def write_wav(path: Path, data: np.ndarray, sample_rate: int) -> None:
    """将浮点信号写入 16-bit PCM .wav 文件"""
    data_clipped = np.clip(data, -1.0, 1.0)
    int_data = (data_clipped * 32767).astype(np.int16)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_data.tobytes())


def get_audio_info(path: Path) -> dict:
    """获取 .wav 文件元信息（手动解析，兼容 IEEE Float）

    @param path - .wav 文件路径
    @returns {sample_rate, channels, duration_sec}
    """
    with open(path, "rb") as f:
        riff = f.read(12)
        if riff[:4] != b"RIFF" or riff[8:12] != b"WAVE":
            raise ValueError("不是有效的 WAV 文件")

        n_channels = 0
        sample_rate = 0
        bits_per_sample = 0
        data_size = 0

        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            chunk_id = chunk_header[:4]
            chunk_size = struct.unpack("<I", chunk_header[4:8])[0]

            if chunk_id == b"fmt ":
                fmt_data = f.read(chunk_size)
                n_channels = struct.unpack("<H", fmt_data[2:4])[0]
                sample_rate = struct.unpack("<I", fmt_data[4:8])[0]
                bits_per_sample = struct.unpack("<H", fmt_data[14:16])[0]
            elif chunk_id == b"data":
                data_size = chunk_size
                f.seek(chunk_size, 1)
            else:
                f.seek(chunk_size, 1)

    bytes_per_sample = bits_per_sample // 8
    n_frames = data_size // (n_channels * bytes_per_sample) if bytes_per_sample > 0 else 0
    duration = n_frames / sample_rate if sample_rate > 0 else 0

    return {
        "sample_rate": sample_rate,
        "channels": n_channels,
        "duration_sec": round(duration, 3),
    }


def resolve_audio_path(filename: str) -> Path:
    """在上传目录和预置目录中查找音频文件，找不到则抛出 FileNotFoundError"""
    upload_path = UPLOAD_DIR / filename
    if upload_path.exists():
        return upload_path

    preset_path = PRESET_AUDIO_DIR / filename
    if preset_path.exists():
        return preset_path

    raise FileNotFoundError(f"找不到音频文件: {filename}")


def generate_delayed_signals(
    source_audio: np.ndarray,
    sample_rate: int,
    sensors: list[tuple[float, float]],
    source_pos: tuple[float, float],
    sound_speed: float,
    snr_db: float | None = None,
) -> list[Path]:
    """根据传感器与声源的几何关系生成各路模拟延迟信号

    @param source_audio - 原始音频（一维浮点数组）
    @param sample_rate  - 采样率
    @param sensors      - 传感器坐标列表
    @param source_pos   - 声源坐标 (x, y)
    @param sound_speed  - 声速 (m/s)
    @param snr_db       - 信噪比（dB），None 表示不加噪声
    @returns 各传感器模拟信号的临时 .wav 文件路径列表
    """
    # 定位信号能量最高帧，确保 GCC-PHAT 首帧包含有效信号
    offset = _find_peak_energy_offset(source_audio)
    if offset > 0:
        logger.info("跳过低能量前段: %d 采样点 (%.3f 秒)", offset, offset / sample_rate)
        source_audio = source_audio[offset:]

    sx, sy = source_pos

    distances = [np.sqrt((sx - x) ** 2 + (sy - y) ** 2) for x, y in sensors]
    travel_times = [d / sound_speed for d in distances]
    min_time = min(travel_times)
    relative_delays = [t - min_time for t in travel_times]
    delay_samples = [int(round(d * sample_rate)) for d in relative_delays]

    logger.info(
        "距离: %s, 相对延迟(采样点): %s",
        [f"{d:.4f}m" for d in distances],
        delay_samples,
    )

    # 用原始信号功率校准噪声，避免延迟零填充稀释功率
    src_power = float(np.mean(source_audio ** 2)) if snr_db is not None else None

    output_paths = []
    sig_len = len(source_audio)

    for i, ds in enumerate(delay_samples):
        delayed = np.zeros(sig_len, dtype=np.float32)
        if ds >= 0 and ds < sig_len:
            delayed[ds:] = source_audio[: sig_len - ds]
        elif ds < 0 and abs(ds) < sig_len:
            delayed[:sig_len + ds] = source_audio[-ds:]

        if snr_db is not None:
            delayed = add_awgn(delayed, snr_db, ref_power=src_power)

        path = TEMP_DIR / f"sensor_{i}.wav"
        write_wav(path, delayed, sample_rate)
        output_paths.append(path)

    return output_paths


def _find_peak_energy_offset(signal: np.ndarray, frame_len: int = 2048) -> int:
    """找到信号中能量最大帧的起始位置，使 GCC-PHAT 处理最强信号段

    @param signal    - 输入信号
    @param frame_len - GCC-PHAT 帧长
    @returns 峰值能量帧的起始采样点索引
    """
    n_frames = len(signal) // frame_len
    if n_frames <= 1:
        return 0
    frames = signal[: n_frames * frame_len].reshape(n_frames, frame_len)
    energies = np.mean(frames ** 2, axis=1)
    return int(np.argmax(energies)) * frame_len


def list_preset_audio() -> list[str]:
    """列出预置音频目录中的 .wav 文件名"""
    if not PRESET_AUDIO_DIR.exists():
        return []
    return sorted(
        f.name for f in PRESET_AUDIO_DIR.iterdir()
        if f.suffix.lower() == ".wav"
    )


def list_uploaded_audio() -> list[str]:
    """列出已上传的 .wav 文件名"""
    return sorted(
        f.name for f in UPLOAD_DIR.iterdir()
        if f.suffix.lower() == ".wav"
    )
