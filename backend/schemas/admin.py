from pydantic import BaseModel
from typing import Optional


class AdminStats(BaseModel):
    total_audios: int
    total_likes: int
    total_dislikes: int
    today_uploads: int


class AdminAudioItem(BaseModel):
    id: int
    nickname: str
    created_at: str
    score: Optional[float] = None
    ai_score: Optional[float] = None
    ai_commentary: Optional[str] = None
    like_count: int
    dislike_count: int

    class Config:
        from_attributes = True
