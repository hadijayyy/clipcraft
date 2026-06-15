"""SQLite database models for ClipCraft"""
import os
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "clipcraft.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = sa.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"
    id = sa.Column(sa.Integer, primary_key=True)
    filename = sa.Column(sa.String, nullable=False)
    original_name = sa.Column(sa.String, nullable=False)
    source = sa.Column(sa.String, default="upload")  # upload or youtube
    source_url = sa.Column(sa.String, nullable=True)
    duration = sa.Column(sa.Float, default=0)
    status = sa.Column(sa.String, default="uploaded")  # uploaded, processing, ready, error
    transcription = sa.Column(sa.Text, nullable=True)
    moments_json = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.DateTime, default=sa.func.now())

class Clip(Base):
    __tablename__ = "clips"
    id = sa.Column(sa.Integer, primary_key=True)
    video_id = sa.Column(sa.Integer, sa.ForeignKey("videos.id"), nullable=False)
    clip_path = sa.Column(sa.String, nullable=False)
    thumbnail_path = sa.Column(sa.String, nullable=True)
    start_time = sa.Column(sa.Float, default=0)
    end_time = sa.Column(sa.Float, default=0)
    mode = sa.Column(sa.String, default="auto")  # auto, manual, split
    subtitles_json = sa.Column(sa.Text, nullable=True)
    overlays_json = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.DateTime, default=sa.func.now())

class StyleExample(Base):
    __tablename__ = "style_examples"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    clip_id = sa.Column(sa.Integer, nullable=True)
    settings_json = sa.Column(sa.Text, nullable=True)
    notes = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.DateTime, default=sa.func.now())

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
