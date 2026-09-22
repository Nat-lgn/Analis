from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime
from datetime import datetime


class Base(DeclarativeBase):
    pass


class GameStat(Base):
    __tablename__ = 'game_stats'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    activity: Mapped[str] = mapped_column(String(50), nullable=False)
    gold: Mapped[int] = mapped_column(Integer, default=0)
    exp: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)