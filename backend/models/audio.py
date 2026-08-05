from sqlalchemy import Column, Integer, Float, String, DateTime, JSON

from .database import Base


class Audio(Base):
    __tablename__ = "audio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nickname = Column(String(50), nullable=True)
    file_path = Column(String(500), nullable=False)
    duration = Column(Float, nullable=False)
    file_size = Column(Integer, nullable=False)
    score = Column(Float, nullable=True)
    score_detail = Column(JSON, nullable=True)
    like_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    # AI 评语（DeepSeek 生成）
    ai_commentary = Column(String(500), nullable=True)        # AI 创意评语
    ai_score = Column(Float, nullable=True)                   # AI 综合评分 0–100
    ai_score_detail = Column(JSON, nullable=True)             # AI 四维度评分详情
    ip_address = Column(String(45), nullable=False)
    created_at = Column(DateTime, nullable=False)
