"""SVM 水下声音分类器 — 后端算法封装"""

import sys
import logging

from config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT / "core" / "src"))
from speech_classifier import classify, load_model

from .base import SpeechClassifier

logger = logging.getLogger(__name__)

MODEL_DIR = PROJECT_ROOT / "core" / "models"


class SvmSpeechClassifier(SpeechClassifier):
    """基于 SVM 的水下声音二分类器（explosion / engine）"""

    def __init__(self):
        model_path = str(MODEL_DIR / "svm_classifier.pkl")
        scaler_path = str(MODEL_DIR / "feature_scaler.pkl")
        self._model, self._scaler = load_model(model_path, scaler_path)
        logger.info("SVM 分类器模型加载完成")

    def predict(self, audio_path: str) -> dict:
        return classify(audio_path, model=self._model, scaler=self._scaler)
