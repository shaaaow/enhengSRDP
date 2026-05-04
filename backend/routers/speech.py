"""语音识别路由 — 接收音频文件名，返回 SVM 分类结果"""

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import SpeechRecognizeRequest, SpeechRecognizeResponse
from services.audio_service import resolve_audio_path
from algorithms.registry import get_speech_classifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/speech", tags=["语音识别"])


@router.post("/recognize", response_model=SpeechRecognizeResponse)
async def recognize_speech(req: SpeechRecognizeRequest):
    """对指定音频文件进行水下声音分类（explosion / engine）"""
    try:
        audio_path = resolve_audio_path(req.audio_file)
    except FileNotFoundError:
        raise HTTPException(404, f"找不到音频文件: {req.audio_file}")

    classifier = get_speech_classifier("svm")

    try:
        result = classifier.predict(str(audio_path))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("语音识别失败: %s", e)
        raise HTTPException(500, f"分类推理失败: {e}")

    return SpeechRecognizeResponse(
        success=True,
        label=result["label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
    )
