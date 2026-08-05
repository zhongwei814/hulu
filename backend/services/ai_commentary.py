"""
AI 评语服务：将 Librosa 评分结果发送给 DeepSeek（OpenAI 兼容 API），
生成创意评语 + AI 四维度评分（节奏 / 能量 / 爆发力 / 感染力）。
"""
import json
import logging

from openai import OpenAI

from config import AI_API_KEY, AI_BASE_URL, AI_MODEL
from models.database import SessionLocal
from models.audio import Audio

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一位专业的鼾声鉴赏师，擅长用诗意、幽默且专业的方式评价打呼噜音频。

用户会提供一段音频的 Librosa 算法分析数据（五维度：响度峰值、频率特色、持续稳定性、动态范围、时长评分，以及综合得分）。

请你：
1. 生成一句创意评语（30–80 字），运用丰富的名词和形容词，风格类似：
   "有种重型机械缓慢驶过月球表面的震撼，低频稳定、爆发力惊人。每 4.2 秒出现一次的峰值，像一台非常守时的拖拉机。"
2. 从以下四个维度打分（0–100，整数）：
   - 节奏：呼噜的节拍感、规律性
   - 能量：响度与爆发力
   - 爆发力：峰值强度与冲击感
   - 感染力：整体听感的"魔性"程度

请严格按以下 JSON 格式返回，不要包含其他内容：
{"commentary": "...", "dimensions": {"节奏": 85, "能量": 92, "爆发力": 78, "感染力": 88}}"""


def generate_commentary(audio_id: int):
    """
    后台任务入口：读取音频的 Librosa 评分数据，调用 AI 生成评语并入库。
    失败时静默退出，不影响主流程。
    """
    if not AI_API_KEY:
        logger.info("AI_API_KEY not configured, skipping AI commentary for audio %s", audio_id)
        return

    db = SessionLocal()
    try:
        audio = db.query(Audio).get(audio_id)
        if audio is None or audio.score_detail is None:
            return

        # 构造用户消息：把 Librosa 五维度数据作为文本传给 AI
        dims = audio.score_detail  # dict: loudness_peak, freq_richness, stability, dynamic_range, duration_score
        user_message = f"""请为以下鼾声数据生成评语和 AI 维度分数：

【Librosa 算法评分】
- 响度峰值：{dims.get('loudness_peak', 'N/A')} 分（权重 30%）
- 频率特色：{dims.get('freq_richness', 'N/A')} 分（权重 25%）
- 持续稳定性：{dims.get('stability', 'N/A')} 分（权重 20%）
- 动态范围：{dims.get('dynamic_range', 'N/A')} 分（权重 15%）
- 时长评分：{dims.get('duration_score', 'N/A')} 分（权重 10%）
- 综合得分：{audio.score} 分

请给出你的专业评语和四维度评分。"""

        client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.9,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()
        # 尝试提取 JSON（处理可能的 markdown 代码块包裹）
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            if content.startswith("json"):
                content = content[4:].strip()

        result = json.loads(content)
        commentary = result.get("commentary", "")
        dimensions = result.get("dimensions", {})

        # 计算 AI 综合分（四维度平均）
        dim_values = [v for v in dimensions.values() if isinstance(v, (int, float))]
        ai_score = round(sum(dim_values) / len(dim_values), 1) if dim_values else None

        audio.ai_commentary = commentary
        audio.ai_score = ai_score
        audio.ai_score_detail = dimensions
        db.commit()

        logger.info(f"AI commentary generated for audio {audio_id}: {commentary[:50]}...")

    except Exception as e:
        db.rollback()
        logger.warning(f"AI commentary failed for audio {audio_id}: {e}")
    finally:
        db.close()
