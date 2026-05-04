"""SVM 水下声音分类器训练脚本"""

import os
import sys
import traceback

import numpy as np
import librosa
import joblib
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report
import warnings

warnings.filterwarnings("ignore")

# ================== 配置参数 ==================
DATA_DIR = "datasets/underwater_sounds"
CLASSES = ["explosion", "engine"]
SAMPLE_RATE = 22050
MAX_LEN = 2.0
MFCC_DIM = 13
ENERGY_THRESH = 1e-4
USE_GRID_SEARCH = True
TEST_SIZE = 0.2
RANDOM_STATE = 42

# 模型输出路径（训练完成后复制到 core/models/）
MODEL_OUTPUT = "../core/models/svm_classifier.pkl"
SCALER_OUTPUT = "../core/models/feature_scaler.pkl"


def find_loudest_segment(y, sr, target_len_samples):
    if len(y) <= target_len_samples:
        return np.pad(y, (0, target_len_samples - len(y)))
    energy = np.convolve(y**2, np.ones(target_len_samples), mode="valid")
    start = np.argmax(energy)
    return y[start : start + target_len_samples]


def extract_features(y, sr):
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


def build_dataset():
    features = []
    labels = []

    for label, class_name in enumerate(CLASSES):
        class_path = os.path.join(DATA_DIR, class_name)
        if not os.path.isdir(class_path):
            print(f"警告：类别文件夹 {class_path} 不存在，跳过。")
            continue

        audio_files = [
            f for f in os.listdir(class_path)
            if f.lower().endswith((".wav", ".mp3", ".flac"))
        ]
        for file in audio_files:
            file_path = os.path.join(class_path, file)
            try:
                y, sr = librosa.load(file_path, sr=SAMPLE_RATE)
            except Exception as e:
                print(f"加载 {file_path} 失败: {e}")
                continue

            target_len_samples = int(SAMPLE_RATE * MAX_LEN)
            y = find_loudest_segment(y, sr, target_len_samples)
            feat = extract_features(y, sr)
            if feat is not None:
                features.append(feat)
                labels.append(label)

        count = sum(1 for l in labels if l == label)
        print(f"类别 '{class_name}': {count} 个有效样本")

    return np.array(features), np.array(labels)


def train_model():
    print("======== 开始训练 ========")
    X, y = build_dataset()

    if len(X) == 0:
        raise RuntimeError(f"在 {DATA_DIR} 中未找到任何有效音频文件")

    print(f"数据集大小: {X.shape}, 类别分布: {np.bincount(y)}")

    unique_labels = np.unique(y)
    if len(unique_labels) < 2:
        raise ValueError(f"数据集中只有一个类别 (标签 {unique_labels})，无法训练")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    if USE_GRID_SEARCH:
        print("正在进行网格搜索...")
        param_grid = {
            "C": [0.1, 1, 10, 100],
            "gamma": ["scale", "auto", 0.01, 0.1],
        }
        base_svm = SVC(
            kernel="rbf", probability=True,
            class_weight="balanced", random_state=RANDOM_STATE,
        )
        grid = GridSearchCV(base_svm, param_grid, cv=3, scoring="f1_macro", n_jobs=1)
        grid.fit(X_train, y_train)
        model = grid.best_estimator_
        print(f"最佳参数: {grid.best_params_}, 交叉验证 F1: {grid.best_score_:.4f}")
    else:
        model = SVC(
            kernel="rbf", C=10, gamma="scale", probability=True,
            class_weight="balanced", random_state=RANDOM_STATE,
        )
        model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\n测试集分类报告：")
    print(classification_report(y_test, y_pred, target_names=CLASSES))

    os.makedirs(os.path.dirname(MODEL_OUTPUT), exist_ok=True)
    joblib.dump(model, MODEL_OUTPUT)
    joblib.dump(scaler, SCALER_OUTPUT)
    print(f"模型已保存: {MODEL_OUTPUT}, {SCALER_OUTPUT}")
    return model, scaler


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("水下声音识别系统训练 (explosion vs engine)")
        print("=" * 60)

        for cls in CLASSES:
            path = os.path.join(DATA_DIR, cls)
            if not os.path.isdir(path):
                print(f"错误：类别文件夹 '{path}' 不存在!")
                sys.exit(1)
            wav_files = [
                f for f in os.listdir(path)
                if f.lower().endswith((".wav", ".mp3", ".flac"))
            ]
            print(f"类别 '{cls}': 找到 {len(wav_files)} 个音频文件")
            if len(wav_files) < 2:
                print(f"错误：类别 '{cls}' 中的音频文件不足 2 个")
                sys.exit(1)

        train_model()
        print("训练完成。")

    except Exception as e:
        print(f"\n训练失败: {e}")
        traceback.print_exc()
        sys.exit(1)
