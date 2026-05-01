"""音频文件上传与获取路由"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from config import UPLOAD_DIR
from models.schemas import AudioUploadResponse, AudioListResponse
from services.audio_service import (
    get_audio_info,
    list_preset_audio,
    list_uploaded_audio,
    resolve_audio_path,
)

router = APIRouter(prefix="/api/audio", tags=["音频管理"])


@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    type: str = Form(..., description="音频类型: engine 或 explosion"),
):
    if type not in ("engine", "explosion"):
        raise HTTPException(400, "type 必须为 'engine' 或 'explosion'")

    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(400, "仅支持 .wav 格式")

    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    try:
        info = get_audio_info(save_path)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(400, f"无法读取音频文件: {e}")

    return AudioUploadResponse(
        filename=file.filename,
        type=type,
        **info,
    )


@router.get("/list", response_model=AudioListResponse)
async def list_audio():
    return AudioListResponse(
        uploads=list_uploaded_audio(),
        presets=list_preset_audio(),
    )


@router.get("/presets")
async def get_presets() -> list[str]:
    return list_preset_audio()


@router.get("/file/{filename}")
async def get_audio_file(filename: str):
    try:
        path = resolve_audio_path(filename)
    except FileNotFoundError:
        raise HTTPException(404, f"找不到文件: {filename}")

    return FileResponse(
        path=str(path),
        media_type="audio/wav",
        filename=filename,
    )
