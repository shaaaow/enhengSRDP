#define _USE_MATH_DEFINES
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <cstdlib>
#include "kiss_fft.h"

using namespace std;

// ============================================================================
// GCC-PHAT 时延估计器
// ============================================================================
class GccPhatEstimator {
private:
    size_t frame_len_;        // 帧长（2 的幂次）
    size_t fft_len_;          // FFT 长度 = 2 × frame_len_
    float  fs_;               // 采样率 (Hz)
    int    max_delay_samples_;// 最大搜索延迟（采样点数）
    float  epsilon_;          // PHAT 加权正则化参数

    kiss_fft_cfg fwd_cfg_;    // 正变换
    kiss_fft_cfg inv_cfg_;    // 逆变换

    vector<float> hann_win_;  // 预计算 Hann 窗

    static bool isPowerOfTwo(size_t n) {
        return n > 0 && (n & (n - 1)) == 0;
    }

    void buildHannWindow() {
        hann_win_.resize(frame_len_);
        for (size_t i = 0; i < frame_len_; ++i) {
            // 周期性 Hann 窗：w[n] = 0.5(1 − cos(2πn / N))
            // 与对称窗（除以 N−1）不同，周期窗满足 COLA 条件，更适合 FFT 分析
            hann_win_[i] = 0.5f * (1.0f - cosf(2.0f * (float)M_PI * i / frame_len_));
        }
    }

    // 去直流偏移：减去帧均值，消除零频能量集中，避免 PHAT 加权在直流处异常
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
    // ========================================================================
    // 构造 / 析构
    // ========================================================================

    /// @param sample_rate   采样率 (Hz)
    /// @param frame_length  帧长，必须为 2 的幂次（如 512、1024、2048）
    /// @param max_delay_sec 最大搜索时延 (秒)，默认 10 ms
    /// @param epsilon       PHAT 正则化系数，默认 1e-10
    GccPhatEstimator(float sample_rate,
                     size_t frame_length,
                     float max_delay_sec = 0.01f,
                     float epsilon = 1e-10f)
        : fs_(sample_rate)
        , frame_len_(frame_length)
        // 零填充到 2N：线性互相关要求至少 N1+N2−1 点，2N 是 ≥ 2N−1 的最小 2 幂
        , fft_len_(2 * frame_length)
        , max_delay_samples_(static_cast<int>(sample_rate * max_delay_sec))
        , epsilon_(epsilon)
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

        // 最大延迟不应超过帧长本身
        if (max_delay_samples_ > (int)frame_len_)
            max_delay_samples_ = (int)frame_len_;
    }

    ~GccPhatEstimator() {
        if (fwd_cfg_) free(fwd_cfg_);
        if (inv_cfg_) free(inv_cfg_);
    }

    // 持有 FFT 配置资源，禁止拷贝
    GccPhatEstimator(const GccPhatEstimator&) = delete;
    GccPhatEstimator& operator=(const GccPhatEstimator&) = delete;

    // ========================================================================
    // 核心方法：GCC-PHAT 时延估计
    //
    // 返回值：时延 τ（秒）。正值表示 sig_target 相对 sig_ref 延迟。
    //
    // 数学定义：
    //   互功率谱  G_xy(f) = X*(f) · Y(f)
    //   PHAT 加权 W(f)    = G_xy(f) / (|G_xy(f)| + ε)
    //   广义互相关 R(τ)   = IFFT{ W(f) }
    //   时延估计   τ_hat  = argmax_τ R(τ)  （在 ±max_delay 范围内搜索）
    // ========================================================================
    float estimateTDOA(const vector<float>& sig_ref,
                       const vector<float>& sig_target)
    {
        if (sig_ref.size() < frame_len_ || sig_target.size() < frame_len_)
            throw invalid_argument("输入信号长度不足帧长");

        // ----- 步骤 1：分帧 -----
        // 截取前 frame_len_ 个采样点作为分析帧
        vector<float> frame_ref(sig_ref.begin(), sig_ref.begin() + frame_len_);
        vector<float> frame_tar(sig_target.begin(), sig_target.begin() + frame_len_);

        // ----- 步骤 2：去直流偏移 -----
        removeDC(frame_ref);
        removeDC(frame_tar);

        // ----- 步骤 3：加 Hann 窗 -----
        applyWindow(frame_ref);
        applyWindow(frame_tar);

        // ----- 步骤 4：零填充并装入复数数组 -----
        // 前 frame_len_ 为有效信号，后 frame_len_ 为零（零填充区域）
        vector<kiss_fft_cpx> in_ref(fft_len_, {0.0f, 0.0f});
        vector<kiss_fft_cpx> in_tar(fft_len_, {0.0f, 0.0f});
        for (size_t i = 0; i < frame_len_; ++i) {
            in_ref[i] = { frame_ref[i], 0.0f };
            in_tar[i] = { frame_tar[i], 0.0f };
        }

        // ----- 步骤 5：FFT -----
        vector<kiss_fft_cpx> X_ref(fft_len_), X_tar(fft_len_);
        kiss_fft(fwd_cfg_, in_ref.data(), X_ref.data());
        kiss_fft(fwd_cfg_, in_tar.data(), X_tar.data());

        // ----- 步骤 6：互功率谱 + PHAT 加权 -----
        //   G_xy(k) = conj(X_ref(k)) * X_tar(k)
        //   实部 = Re(X_ref)*Re(X_tar) + Im(X_ref)*Im(X_tar)
        //   虚部 = Im(X_ref)*Re(X_tar) − Re(X_ref)*Im(X_tar)
        //   W(k) = G_xy(k) / (|G_xy(k)| + ε)
        vector<kiss_fft_cpx> G_phat(fft_len_);
        for (size_t k = 0; k < fft_len_; ++k) {
            float re = X_ref[k].r * X_tar[k].r + X_ref[k].i * X_tar[k].i;
            // conj(X_ref) * X_tar 的虚部 = Re(X_ref)*Im(X_tar) − Im(X_ref)*Re(X_tar)
            float im = X_ref[k].r * X_tar[k].i - X_ref[k].i * X_tar[k].r;

            float mag = sqrtf(re * re + im * im) + epsilon_;
            G_phat[k].r = re / mag;
            G_phat[k].i = im / mag;
        }

        // ----- 步骤 7：IFFT -----
        vector<kiss_fft_cpx> gcc_cpx(fft_len_);
        kiss_fft(inv_cfg_, G_phat.data(), gcc_cpx.data());

        // kiss_fft 的 IFFT 不包含 1/N 归一化因子，手动除以 fft_len_
        const float norm = 1.0f / (float)fft_len_;
        vector<float> gcc(fft_len_);
        for (size_t i = 0; i < fft_len_; ++i)
            gcc[i] = gcc_cpx[i].r * norm;

        // ----- 步骤 8：峰值检测（受限搜索范围）-----
        //
        // IFFT 输出的延迟布局（循环卷积性质）：
        //   gcc[0]              → τ =  0  采样点
        //   gcc[1 .. N/2]       → τ = +1 .. +N/2  （正延迟：目标比参考晚到）
        //   gcc[N/2+1 .. N-1]   → τ = -(N/2-1) .. -1  （负延迟：目标比参考早到）
        //
        // 只在 ±max_delay_samples_ 范围内搜索，避免拾取噪声旁瓣
        float best_val = -1e30f;
        int   best_idx = 0;

        // 正延迟区间：[0, min(max_delay, N/2)]
        int pos_end = min(max_delay_samples_, (int)fft_len_ / 2);
        for (int i = 0; i <= pos_end; ++i) {
            if (gcc[i] > best_val) {
                best_val = gcc[i];
                best_idx = i;
            }
        }
        // 负延迟区间：[N − max_delay, N − 1]
        int neg_start = max((int)fft_len_ - max_delay_samples_,
                            (int)fft_len_ / 2 + 1);
        for (int i = neg_start; i < (int)fft_len_; ++i) {
            if (gcc[i] > best_val) {
                best_val = gcc[i];
                best_idx = i;
            }
        }

        // 循环索引 → 有符号延迟（采样点）
        int delay_samples = best_idx;
        if (best_idx > (int)fft_len_ / 2)
            delay_samples = best_idx - (int)fft_len_;

        // ----- 步骤 9：亚采样抛物线插值 -----
        //
        // 以峰值及其左右邻点 (y_{-1}, y_0, y_{+1}) 拟合抛物线
        //   δ = 0.5 × (y_{-1} − y_{+1}) / (y_{-1} − 2y_0 + y_{+1})
        //
        // 使用取模索引确保在数组边界处正确回绕（循环互相关的连续性）
        int idx_prev = ((best_idx - 1) + (int)fft_len_) % (int)fft_len_;
        int idx_next = (best_idx + 1) % (int)fft_len_;

        float y_prev = gcc[idx_prev];
        float y_peak = gcc[best_idx];
        float y_next = gcc[idx_next];

        float denom = y_prev - 2.0f * y_peak + y_next;
        float delta = 0.0f;
        if (fabsf(denom) > 1e-12f) {
            delta = 0.5f * (y_prev - y_next) / denom;
            // 限幅：|δ| > 0.5 意味着真正的极值不在 best_idx 附近，插值失效
            delta = max(-0.5f, min(0.5f, delta));
        }

        // ----- 步骤 10：输出时延估计（秒）-----
        float tdoa = (delay_samples + delta) / fs_;
        return tdoa;
    }

    // ========================================================================
    // 访问器
    // ========================================================================
    size_t frameLength()      const { return frame_len_; }
    size_t fftLength()        const { return fft_len_; }
    float  sampleRate()       const { return fs_; }
    int    maxDelaySamples()  const { return max_delay_samples_; }
};


// ============================================================================
// 测试辅助：生成整数延迟信号（仅用于验证，不属于 GccPhatEstimator）
// ============================================================================
static vector<float> makeDelayedSignal(const vector<float>& src, int delay_samples) {
    vector<float> out(src.size(), 0.0f);
    for (int i = 0; i < (int)src.size(); ++i) {
        int j = i - delay_samples;
        if (j >= 0 && j < (int)src.size())
            out[i] = src[j];
    }
    return out;
}


// ============================================================================
// 测试入口
// ============================================================================
int main() {
    // ===== 参数配置 =====
    const float  fs         = 48000.0f;    // 采样率 48 kHz
    const size_t frame_len  = 2048;        // 帧长 2048 点
    const float  sound_speed = 1500.0f;    // 水中声速 (m/s)
    const float  max_delay  = 0.01f;       // 最大搜索时延 10 ms

    GccPhatEstimator estimator(fs, frame_len, max_delay);

    cout << "===== GCC-PHAT 时延估计测试 =====" << endl;
    cout << "采样率:   " << fs << " Hz" << endl;
    cout << "帧长:     " << frame_len << " 点" << endl;
    cout << "FFT 长度: " << estimator.fftLength() << " 点（含零填充）" << endl;
    cout << endl;

    // ===== 生成测试信号（白噪声）=====
    srand(42);
    const int sig_len = 8192;
    vector<float> source(sig_len);
    for (int i = 0; i < sig_len; ++i)
        source[i] = ((float)rand() / RAND_MAX) * 2.0f - 1.0f;

    // ===== 测试 1：正延迟 =====
    {
        int true_delay = 15;  // 采样点
        float true_tdoa = (float)true_delay / fs;

        vector<float> mic_ref = source;
        vector<float> mic_tar = makeDelayedSignal(source, true_delay);

        float est_tdoa = estimator.estimateTDOA(mic_ref, mic_tar);

        cout << "[测试 1] 正延迟" << endl;
        cout << "  真实延迟: " << true_delay << " 样本 = "
             << true_tdoa * 1000.0f << " ms" << endl;
        cout << "  估计时延: " << est_tdoa * 1000.0f << " ms" << endl;
        cout << "  误差:     " << fabsf(est_tdoa - true_tdoa) * 1e6f << " μs"
             << endl << endl;
    }

    // ===== 测试 2：负延迟 =====
    {
        int true_delay = -10;
        float true_tdoa = (float)true_delay / fs;

        vector<float> mic_ref = source;
        vector<float> mic_tar = makeDelayedSignal(source, true_delay);

        float est_tdoa = estimator.estimateTDOA(mic_ref, mic_tar);

        cout << "[测试 2] 负延迟" << endl;
        cout << "  真实延迟: " << true_delay << " 样本 = "
             << true_tdoa * 1000.0f << " ms" << endl;
        cout << "  估计时延: " << est_tdoa * 1000.0f << " ms" << endl;
        cout << "  误差:     " << fabsf(est_tdoa - true_tdoa) * 1e6f << " μs"
             << endl << endl;
    }

    // ===== 测试 3：零延迟 =====
    {
        float est_tdoa = estimator.estimateTDOA(source, source);

        cout << "[测试 3] 零延迟" << endl;
        cout << "  真实延迟: 0 样本" << endl;
        cout << "  估计时延: " << est_tdoa * 1e6f << " μs" << endl;
        cout << "  误差:     " << fabsf(est_tdoa) * 1e6f << " μs"
             << endl << endl;
    }

    // ===== 测试 4：模拟水声场景（距离差 → TDOA）=====
    {
        float d1 = 10.0f;    // 参考水听器距声源距离 (m)
        float d2 = 11.5f;    // 目标水听器距声源距离 (m)
        float true_tdoa = (d2 - d1) / sound_speed;
        int   delay_samples = static_cast<int>(round(true_tdoa * fs));

        vector<float> mic_ref = source;
        vector<float> mic_tar = makeDelayedSignal(source, delay_samples);

        float est_tdoa = estimator.estimateTDOA(mic_ref, mic_tar);

        cout << "[测试 4] 水声场景：d1=" << d1 << " m, d2=" << d2 << " m" << endl;
        cout << "  理论 TDOA: " << true_tdoa * 1000.0f << " ms ("
             << delay_samples << " 样本)" << endl;
        cout << "  估计 TDOA: " << est_tdoa * 1000.0f << " ms" << endl;
        cout << "  误差:      " << fabsf(est_tdoa - true_tdoa) * 1e6f << " μs"
             << endl;
        cout << "  等效距离误差: "
             << fabsf(est_tdoa - true_tdoa) * sound_speed * 100.0f << " cm"
             << endl;
    }

    std::cin.get();
    return 0;
}
