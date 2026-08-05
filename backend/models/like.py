from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, ForeignKey

from .database import Base


class Like(Base):
    __tablename__ = "like"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audio_id = Column(Integer, ForeignKey("audio.id"), nullable=False)
    ip_address = Column(String(45), nullable=False)
    created_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("audio_id", "ip_address", name="uq_like_audio_ip"),
    )
