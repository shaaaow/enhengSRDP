"""项目路径与默认参数配置"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GCC_PHAT_EXE = PROJECT_ROOT / "build" / "GCC-PHAT-test.exe"
PRESET_AUDIO_DIR = PROJECT_ROOT / "audio"

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

TEMP_DIR = UPLOAD_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

DEFAULT_SOUND_SPEED = 1500.0
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_FRAME_LEN = 2048
DEFAULT_MAX_DELAY = 0.025
