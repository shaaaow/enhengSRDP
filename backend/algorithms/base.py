"""算法抽象基类 — 新增算法继承对应基类后在 registry.py 注册即可"""

from abc import ABC, abstractmethod


class TDOAEstimator(ABC):
    """TDOA 估计算法基类"""

    @abstractmethod
    async def estimate(
        self,
        ref_path: str,
        target_path: str,
        sample_rate: int = 48000,
        frame_len: int = 2048,
        max_delay: float = 0.01,
    ) -> dict:
        """
        @param ref_path    - 参考信号 .wav 路径
        @param target_path - 目标信号 .wav 路径
        @param sample_rate - 采样率
        @param frame_len   - 帧长
        @param max_delay   - 最大搜索延迟（秒）
        @returns {tdoa_sec: float, peak_value: float, ...}
        """
        ...


class SourceLocalizer(ABC):
    """声源定位算法基类"""

    @abstractmethod
    def localize(
        self,
        sensors: list[tuple[float, float]],
        tdoa_values: list[float],
        sound_speed: float = 1500.0,
    ) -> dict:
        """
        @param sensors     - 传感器坐标列表 [(x1,y1), ...]
        @param tdoa_values - 以第一个传感器为参考的 TDOA 列表（秒）
        @param sound_speed - 声速（m/s）
        @returns {x: float, y: float, gdop: float, ...}
        """
        ...


class SpeechClassifier(ABC):
    """声音分类算法基类"""

    @abstractmethod
    def predict(self, audio_path: str) -> dict:
        """
        @param audio_path - 音频文件路径
        @returns {label: str, confidence: float, probabilities: dict}
        """
        ...
