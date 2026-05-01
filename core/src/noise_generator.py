"""高斯白噪声发生器 — 按指定 SNR 向信号叠加加性白高斯噪声（AWGN）"""

import numpy as np


def add_awgn(
    signal: np.ndarray,
    snr_db: float,
    ref_power: float | None = None,
) -> np.ndarray:
    """
    @param signal    - 输入信号（一维浮点数组）
    @param snr_db    - 目标信噪比（dB），None 或 inf 表示不加噪
    @param ref_power - 参考信号功率（用于校准噪声），None 时从 signal 计算
    @returns 叠加噪声后的信号（与输入等长）
    """
    if snr_db is None or np.isinf(snr_db):
        return signal.copy()

    power = ref_power if ref_power is not None else float(np.mean(signal ** 2))
    if power < 1e-20:
        return signal.copy()

    noise_power = power / (10.0 ** (snr_db / 10.0))
    noise = np.random.normal(0.0, np.sqrt(noise_power), len(signal)).astype(signal.dtype)
    return signal + noise
