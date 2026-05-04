"""水下声音 SVM 分类器 — 推理模块"""

import numpy as np
import librosa
import joblib

CLASSES = ["explosion", "engine"]
SAMPLE_RATE = 22050
MAX_LEN = 2.0
MFCC_DIM = 13
ENERGY_THRESH = 1e-4


def _find_loudest_segment(y: np.ndarray, target_len: int) -> np.ndarray:
    if len(y) <= target_len:
        return np.pad(y, (0, target_len - len(y)))
    energy = np.convolve(y**2, np.ones(target_len), mode="valid")
    start = np.argmax(energy)
    return y[start : start + target_len]


def _extract_features(y: np.ndarray, sr: int) -> np.ndarray | None:
    rms = np.sqrt(np.mean(y**2))
    if rms < ENERGY_THRESH:
        return None

    y = librosa.effects.preemphasis(y, coef=0.97)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=MFCC_DIM)
    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)

    delta = librosa.feature.delta(mfcc)
    delta2 = librosa.feature.delta(mfcc, order=2)

    cent = librosa.feature.spectral_centroid(y=y, sr=sr)
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y)

    return np.concatenate([
        mfcc_mean, mfcc_std,
        np.mean(delta, axis=1), np.std(delta, axis=1),
        np.mean(delta2, axis=1), np.std(delta2, axis=1),
        [np.mean(cent), np.std(cent)],
        [np.mean(bandwidth), np.std(bandwidth)],
        [np.mean(zcr), np.std(zcr)],
    ])


def load_model(model_path: str, scaler_path: str):
    """加载 SVM 模型和 scaler，供外部缓存复用"""
    return joblib.load(model_path), joblib.load(scaler_path)


def classify(file_path: str, model=None, scaler=None, *, model_path: str = "", scaler_path: str = "") -> dict:
    """对单个音频文件进行水下声音分类

    @param file_path    - 待识别音频路径
    @param model        - 已加载的 SVM 模型（优先使用）
    @param scaler       - 已加载的 StandardScaler（优先使用）
    @param model_path   - SVM 模型 .pkl 路径（model 为 None 时使用）
    @param scaler_path  - StandardScaler .pkl 路径（scaler 为 None 时使用）
    @returns {label, confidence, probabilities}
    """
    if model is None or scaler is None:
        model, scaler = load_model(model_path, scaler_path)

    y, sr = librosa.load(file_path, sr=SAMPLE_RATE)
    target_len = int(SAMPLE_RATE * MAX_LEN)
    y = _find_loudest_segment(y, target_len)
    feat = _extract_features(y, sr)

    if feat is None:
        raise ValueError("音频能量过低，无法提取有效特征")

    feat_scaled = scaler.transform(feat.reshape(1, -1))
    pred_class = model.predict(feat_scaled)[0]
    proba = model.predict_proba(feat_scaled)[0]

    return {
        "label": CLASSES[pred_class],
        "confidence": float(proba[pred_class]),
        "probabilities": {cls: float(p) for cls, p in zip(CLASSES, proba)},
    }
