"""GCC-PHAT C++ 可执行文件的 subprocess 封装"""

import json
import subprocess
import asyncio
import logging
from pathlib import Path

from .base import TDOAEstimator
from config import GCC_PHAT_EXE

logger = logging.getLogger(__name__)


def _run_gcc_phat(cmd: list[str]) -> dict:
    """同步调用 C++ 程序并解析 JSON 输出"""
    proc = subprocess.run(
        cmd,
        capture_output=True,
        timeout=30,
    )

    if proc.returncode != 0:
        err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"GCC-PHAT 执行失败 (退出码 {proc.returncode}): {err_msg}")

    try:
        result = json.loads(proc.stdout.decode("utf-8"))
    except json.JSONDecodeError as e:
        raw = proc.stdout.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"GCC-PHAT 输出解析失败: {e}\n原始输出: {raw}")

    return result


class GccPhatCppEstimator(TDOAEstimator):
    """通过 subprocess 调用 C++ GCC-PHAT 进行 TDOA 估计"""

    async def estimate(
        self,
        ref_path: str,
        target_path: str,
        sample_rate: int = 48000,
        frame_len: int = 2048,
        max_delay: float = 0.01,
    ) -> dict:
        if not GCC_PHAT_EXE.exists():
            raise FileNotFoundError(f"找不到 C++ 可执行文件: {GCC_PHAT_EXE}")

        cmd = [
            str(GCC_PHAT_EXE),
            "--ref", str(ref_path),
            "--target", str(target_path),
            "--frame-len", str(frame_len),
            "--max-delay", str(max_delay),
        ]

        logger.info("调用 GCC-PHAT: %s", " ".join(cmd))

        return await asyncio.to_thread(_run_gcc_phat, cmd)
