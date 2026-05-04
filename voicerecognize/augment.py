"""数据增强脚本 — 从原始爆炸声生成变体样本"""

import os
import random

import librosa
import soundfile as sf
import numpy as np

INPUT_DIR = "datasets/explosion_sounds/originals"
OUTPUT_DIR = "datasets/explosion_sounds/variants"
TOTAL_VARIANTS = 510


def add_noise(data, noise_factor=0.005):
    noise = np.random.randn(len(data))
    return data + noise_factor * noise


def shift_pitch(data, sr, n_steps):
    return librosa.effects.pitch_shift(y=data, sr=sr, n_steps=n_steps)


def change_speed(data, rate):
    return librosa.effects.time_stretch(y=data, rate=rate)


def change_volume(data, factor):
    return data * factor


def process_file(file_path, base_name, variants_needed):
    y, sr = librosa.load(file_path, sr=None)
    for i in range(variants_needed):
        y_aug = np.copy(y)
        if random.random() > 0.3:
            y_aug = add_noise(y_aug, noise_factor=random.uniform(0.001, 0.015))
        if random.random() > 0.3:
            y_aug = shift_pitch(y_aug, sr, n_steps=random.uniform(-3.0, 3.0))
        if random.random() > 0.3:
            y_aug = change_speed(y_aug, rate=random.uniform(0.8, 1.2))
        if random.random() > 0.3:
            y_aug = change_volume(y_aug, factor=random.uniform(0.6, 1.4))

        output_filename = f"{base_name}_variant_{i + 1}.wav"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        sf.write(output_path, y_aug, sr)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(INPUT_DIR):
        print(f"错误：找不到 '{INPUT_DIR}' 目录，请确认路径。")
        return

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith((".wav", ".WAV"))]
    if len(files) == 0:
        print(f"在 '{INPUT_DIR}' 目录下没有找到 WAV 文件。")
        return

    print(f"找到 {len(files)} 个原始文件。开始生成...")
    base_variants_per_file = TOTAL_VARIANTS // len(files)
    remainder = TOTAL_VARIANTS % len(files)

    for idx, file in enumerate(files):
        file_path = os.path.join(INPUT_DIR, file)
        base_name = os.path.splitext(file)[0]
        current_variants_needed = base_variants_per_file + (1 if idx < remainder else 0)
        print(f"正在处理: {file} -> 将生成 {current_variants_needed} 个变体...")
        process_file(file_path, base_name, current_variants_needed)

    print(f"\n全部完成！生成 {TOTAL_VARIANTS} 个音频变体，保存在 '{OUTPUT_DIR}' 目录下。")


if __name__ == "__main__":
    main()
