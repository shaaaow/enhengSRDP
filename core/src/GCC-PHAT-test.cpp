#define _USE_MATH_DEFINES
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <cstdlib>
#include <string>
#include <sstream>
#include "kiss_fft.h"
#include "AudioFile.h"

using namespace std;

/**
 * GCC-PHAT 时延估计器
 *
 * @param sample_rate   采样率 (Hz)
 * @param frame_length  帧长，必须为 2 的幂次
 * @param max_delay_sec 最大搜索时延 (秒)
 * @param epsilon       PHAT 正则化系数
 */
class GccPhatEstimator {
private:
    size_t frame_len_;
    size_t fft_len_;
    float  fs_;
    int    max_delay_samples_;
    float  epsilon_;
    float  last_peak_value_;

    kiss_fft_cfg fwd_cfg_;
    kiss_fft_cfg inv_cfg_;

    vector<float> hann_win_;

    static bool isPowerOfTwo(size_t n) {
        return n > 0 && (n & (n - 1)) == 0;
    }

    // 周期性 Hann 窗，满足 COLA 条件
    void buildHannWindow() {
        hann_win_.resize(frame_len_);
        for (size_t i = 0; i < frame_len_; ++i) {
            hann_win_[i] = 0.5f * (1.0f - cosf(2.0f * (float)M_PI * i / frame_len_));
        }
    }

    static void removeDC(vector<float>& frame) {
        float mean = accumulate(frame.begin(), frame.end(), 0.0f)
                     / (float)frame.size();
        for (auto& s : frame) s -= mean;
    }

    void applyWindow(vector<float>& frame) const {
        for (size_t i = 0; i < frame_len_ && i < frame.size(); ++i) {
            frame[i] *= hann_win_[i];
        }
    }

public:
    GccPhatEstimator(float sample_rate,
                     size_t frame_length,
                     float max_delay_sec = 0.025f,
                     float epsilon = 1e-10f)
        : fs_(sample_rate)
        , frame_len_(frame_length)
        , fft_len_(2 * frame_length)
        , max_delay_samples_(static_cast<int>(sample_rate * max_delay_sec))
        , epsilon_(epsilon)
        , last_peak_value_(0.0f)
        , fwd_cfg_(nullptr)
        , inv_cfg_(nullptr)
    {
        if (!isPowerOfTwo(frame_len_))
            throw invalid_argument("帧长必须为 2 的幂次");
        if (fs_ <= 0.0f)
            throw invalid_argument("采样率必须为正数");

        fwd_cfg_ = kiss_fft_alloc(fft_len_, 0, nullptr, nullptr);
        inv_cfg_ = kiss_fft_alloc(fft_len_, 1, nullptr, nullptr);
        if (!fwd_cfg_ || !inv_cfg_)
            throw runtime_error("FFT 配置分配失败");

        buildHannWindow();

        if (max_delay_samples_ > (int)frame_len_)
            max_delay_samples_ = (int)frame_len_;
    }

    ~GccPhatEstimator() {
        if (fwd_cfg_) free(fwd_cfg_);
        if (inv_cfg_) free(inv_cfg_);
    }

    GccPhatEstimator(const GccPhatEstimator&) = delete;
    GccPhatEstimator& operator=(const GccPhatEstimator&) = delete;

    /**
     * GCC-PHAT 时延估计
     * @returns 时延 τ（秒），正值表示 sig_target 相对 sig_ref 延迟
     */
    float estimateTDOA(const vector<float>& sig_ref,
                       const vector<float>& sig_target)
    {
        if (sig_ref.size() < frame_len_ || sig_target.size() < frame_len_)
            throw invalid_argument("输入信号长度不足帧长");

        vector<float> frame_ref(sig_ref.begin(), sig_ref.begin() + frame_len_);
        vector<float> frame_tar(sig_target.begin(), sig_target.begin() + frame_len_);

        removeDC(frame_ref);
        removeDC(frame_tar);
        applyWindow(frame_ref);
        applyWindow(frame_tar);

        vector<kiss_fft_cpx> in_ref(fft_len_, {0.0f, 0.0f});
        vector<kiss_fft_cpx> in_tar(fft_len_, {0.0f, 0.0f});
        for (size_t i = 0; i < frame_len_; ++i) {
            in_ref[i] = { frame_ref[i], 0.0f };
            in_tar[i] = { frame_tar[i], 0.0f };
        }

        vector<kiss_fft_cpx> X_ref(fft_len_), X_tar(fft_len_);
        kiss_fft(fwd_cfg_, in_ref.data(), X_ref.data());
        kiss_fft(fwd_cfg_, in_tar.data(), X_tar.data());

        vector<kiss_fft_cpx> G_phat(fft_len_);
        for (size_t k = 0; k < fft_len_; ++k) {
            float re = X_ref[k].r * X_tar[k].r + X_ref[k].i * X_tar[k].i;
            float im = X_ref[k].r * X_tar[k].i - X_ref[k].i * X_tar[k].r;
            float mag = sqrtf(re * re + im * im) + epsilon_;
            G_phat[k].r = re / mag;
            G_phat[k].i = im / mag;
        }

        vector<kiss_fft_cpx> gcc_cpx(fft_len_);
        kiss_fft(inv_cfg_, G_phat.data(), gcc_cpx.data());

        const float norm = 1.0f / (float)fft_len_;
        vector<float> gcc(fft_len_);
        for (size_t i = 0; i < fft_len_; ++i)
            gcc[i] = gcc_cpx[i].r * norm;

        float best_val = -1e30f;
        int   best_idx = 0;

        int pos_end = min(max_delay_samples_, (int)fft_len_ / 2);
        for (int i = 0; i <= pos_end; ++i) {
            if (gcc[i] > best_val) {
                best_val = gcc[i];
                best_idx = i;
            }
        }
        int neg_start = max((int)fft_len_ - max_delay_samples_,
                            (int)fft_len_ / 2 + 1);
        for (int i = neg_start; i < (int)fft_len_; ++i) {
            if (gcc[i] > best_val) {
                best_val = gcc[i];
                best_idx = i;
            }
        }

        last_peak_value_ = best_val;

        int delay_samples = best_idx;
        if (best_idx > (int)fft_len_ / 2)
            delay_samples = best_idx - (int)fft_len_;

        // 亚采样抛物线插值
        int idx_prev = ((best_idx - 1) + (int)fft_len_) % (int)fft_len_;
        int idx_next = (best_idx + 1) % (int)fft_len_;

        float y_prev = gcc[idx_prev];
        float y_peak = gcc[best_idx];
        float y_next = gcc[idx_next];

        float denom = y_prev - 2.0f * y_peak + y_next;
        float delta = 0.0f;
        if (fabsf(denom) > 1e-12f) {
            delta = 0.5f * (y_prev - y_next) / denom;
            delta = max(-0.5f, min(0.5f, delta));
        }

        return (delay_samples + delta) / fs_;
    }

    size_t frameLength()      const { return frame_len_; }
    size_t fftLength()        const { return fft_len_; }
    float  sampleRate()       const { return fs_; }
    int    maxDelaySamples()  const { return max_delay_samples_; }
    float  lastPeakValue()    const { return last_peak_value_; }
};


/**
 * 命令行入口
 * 用法: GCC-PHAT-test.exe --ref <ref.wav> --target <target.wav>
 *                         [--frame-len 2048] [--max-delay 0.025]
 */

static void printUsage(const char* prog) {
    cerr << "用法: " << prog
         << " --ref <参考信号.wav> --target <目标信号.wav>"
         << " [--frame-len 2048] [--max-delay 0.025]" << endl;
}

int main(int argc, char* argv[]) {
    string ref_path, target_path;
    size_t frame_len = 2048;
    float  max_delay = 0.025f;

    for (int i = 1; i < argc; ++i) {
        string arg = argv[i];
        if (arg == "--ref" && i + 1 < argc) {
            ref_path = argv[++i];
        } else if (arg == "--target" && i + 1 < argc) {
            target_path = argv[++i];
        } else if (arg == "--frame-len" && i + 1 < argc) {
            frame_len = (size_t)atoi(argv[++i]);
        } else if (arg == "--max-delay" && i + 1 < argc) {
            max_delay = (float)atof(argv[++i]);
        } else if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return 0;
        }
    }

    if (ref_path.empty() || target_path.empty()) {
        printUsage(argv[0]);
        return 1;
    }

    AudioFile<float> ref_audio, target_audio;

    if (!ref_audio.load(ref_path)) {
        cerr << "错误: 无法读取参考信号文件: " << ref_path << endl;
        return 1;
    }
    if (!target_audio.load(target_path)) {
        cerr << "错误: 无法读取目标信号文件: " << target_path << endl;
        return 1;
    }

    const vector<float>& sig_ref = ref_audio.samples[0];
    const vector<float>& sig_tar = target_audio.samples[0];
    float sample_rate = (float)ref_audio.getSampleRate();

    try {
        GccPhatEstimator estimator(sample_rate, frame_len, max_delay);
        float tdoa = estimator.estimateTDOA(sig_ref, sig_tar);
        float peak_value = estimator.lastPeakValue();

        ostringstream json;
        json.precision(8);
        json << "{";
        json << "\"tdoa_sec\":" << tdoa;
        json << ",\"peak_value\":" << peak_value;
        json << ",\"sample_rate\":" << (int)sample_rate;
        json << ",\"frame_length\":" << frame_len;
        json << ",\"fft_length\":" << estimator.fftLength();
        json << "}";

        cout << json.str() << endl;

    } catch (const exception& e) {
        cerr << "错误: " << e.what() << endl;
        return 1;
    }

    return 0;
}
