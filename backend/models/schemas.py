"""Pydantic 请求/响应模型"""

from pydantic import BaseModel, Field
from datetime import datetime


class SensorPosition(BaseModel):
    id: str
    x: float
    y: float


class SourcePosition(BaseModel):
    x: float
    y: float


class AudioUploadResponse(BaseModel):
    filename: str
    type: str = Field(description="engine 或 explosion")
    sample_rate: int
    channels: int
    duration_sec: float


class AudioListResponse(BaseModel):
    uploads: list[str]
    presets: list[str]


class SimulationRequest(BaseModel):
    sensors: list[SensorPosition] = Field(min_length=3, max_length=3)
    source: SourcePosition
    audio_file: str = Field(description="音频文件名（上传或预置）")
    sound_speed: float = Field(default=1500.0, gt=0)
    snr_db: float | None = Field(default=None, description="信噪比（dB），None 表示不加噪声")


class TDOAResult(BaseModel):
    dt12: float = Field(description="M1-M2 时延差（秒）")
    dt13: float = Field(description="M1-M3 时延差（秒）")
    dt23: float = Field(description="M2-M3 时延差（秒）")
    dt12_theoretical: float = Field(description="M1-M2 理论时延差（秒）")
    dt13_theoretical: float = Field(description="M1-M3 理论时延差（秒）")
    dt23_theoretical: float = Field(description="M2-M3 理论时延差（秒）")
    gcc_peak_12: float = Field(description="M1-M2 GCC 峰值")
    gcc_peak_13: float = Field(description="M1-M3 GCC 峰值")
    gcc_peak_23: float = Field(description="M2-M3 GCC 峰值")


class LocalizationResult(BaseModel):
    x: float = Field(description="估计 X 坐标（米）")
    y: float = Field(description="估计 Y 坐标（米）")
    gdop: float = Field(description="几何精度稀释因子")
    gdop_quality: str = Field(description="布局质量评价")
    error_estimate_m: float = Field(description="定位误差（米）")


class SimulationResponse(BaseModel):
    success: bool
    message: str = ""
    tdoa: TDOAResult | None = None
    localization: LocalizationResult | None = None
    snr_db: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SpeechRecognizeRequest(BaseModel):
    audio_file: str = Field(description="音频文件名（上传或预置）")


class SpeechRecognizeResponse(BaseModel):
    success: bool
    label: str = Field(description="分类结果: explosion 或 engine")
    confidence: float = Field(description="分类置信度 [0, 1]")
    probabilities: dict[str, float] = Field(description="各类别概率")
