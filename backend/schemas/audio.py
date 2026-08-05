from pydantic import BaseModel
from typing import Optional


class AudioUploadResponse(BaseModel):
    id: int
    nickname: str
    message: str


class AudioDetail(BaseModel):
    id: int
    nickname: str
    duration: float
    score: Optional[float] = None
    score_detail: Optional[dict] = None
    ai_commentary: Optional[str] = None
    ai_score: Optional[float] = None
    ai_score_detail: Optional[dict] = None
    like_count: int
    dislike_count: int
    created_at: str
    stream_url: str
    waveform_url: str

    class Config:
        from_attributes = True


class LeaderboardItem(BaseModel):
    id: int
    nickname: str
    duration: float
    score: Optional[float] = None
    ai_score: Optional[float] = None
    like_count: int
    dislike_count: int
    created_at: str

    class Config:
        from_attributes = True
