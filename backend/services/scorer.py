import librosa
import numpy as np

from models.database import SessionLocal
from models.audio import Audio

SAMPLE_RATE = 22050


def score_audio(audio_id: int):
    """后台任务入口：加载音频并计算五维度评分。"""
    db = SessionLocal()
    try:
        audio = db.query(Audio).get(audio_id)
        if audio is None:
            return

        y, sr = librosa.load(audio.file_path, sr=SAMPLE_RATE)
        duration = len(y) / sr

        dims = {
            "loudness_peak": _calc_loudness(y),
            "freq_richness": _calc_freq_richness(y, sr),
            "stability": _calc_stability(y),
            "dynamic_range": _calc_dynamic_range(y),
            "duration_score": _calc_duration_score(duration),
        }

        total = round(
            dims["loudness_peak"] * 0.30
            + dims["freq_richness"] * 0.25
            + dims["stability"] * 0.20
            + dims["dynamic_range"] * 0.15
            + dims["duration_score"] * 0.10,
            1,
        )

        audio.score = total
        audio.score_detail = dims
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    # Librosa 评分完成后，独立触发 AI 评语（AI 调用失败不影响评分结果）
    try:
        from .ai_commentary import generate_commentary
        generate_commentary(audio_id)
    except Exception:
        pass  # AI 评语失败静默，不影响主流程


# ---- 五个维度计算 ----

def _calc_loudness(y: np.ndarray) -> float:
    """响度峰值：RMS 能量 95 分位，归一化到 0–100。"""
    try:
        rms = librosa.feature.rms(y=y).flatten()
        peak = np.percentile(rms, 95)
        return round(min(peak * 500, 100), 1)  # 放大后截断
    except Exception:
        return 50.0


def _calc_freq_richness(y: np.ndarray, sr: int) -> float:
    """频率特色：频谱质心标准差归一化。"""
    try:
        centroids = librosa.feature.spectral_centroid(y=y, sr=sr).flatten()
        std = np.std(centroids)
        return round(min(std / 10, 100), 1)
    except Exception:
        return 50.0


def _calc_stability(y: np.ndarray) -> float:
    """持续稳定性：分段 RMS 方差，越稳分越高。"""
    try:
        rms = librosa.feature.rms(y=y).flatten()
        if len(rms) < 2:
            return 50.0
        variance = np.var(rms)
        return round(max(0, 100 - variance * 1000), 1)
    except Exception:
        return 50.0


def _calc_dynamic_range(y: np.ndarray) -> float:
    """动态范围：RMS 最大值与中位数的比值。"""
    try:
        rms = librosa.feature.rms(y=y).flatten()
        rms = rms[rms > 0]
        if len(rms) < 2:
            return 50.0
        ratio = np.max(rms) / np.median(rms)
        return round(min(ratio * 30, 100), 1)
    except Exception:
        return 50.0


def _calc_duration_score(duration: float) -> float:
    """时长评分：30–120 秒满分，<10 秒 0 分，>120 秒线性衰减。"""
    if duration < 10:
        return 0.0
    if 30 <= duration <= 120:
        return 100.0
    if duration < 30:
        return round((duration - 10) / 20 * 100, 1)
    return round(max(0, 100 - (duration - 120) / 60 * 50), 1)
