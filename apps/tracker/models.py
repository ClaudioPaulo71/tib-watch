from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from apps.auth.models import User

class Media(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tmdb_id: int = Field(index=True) # Not unique globally because ID collision might happen between movie/tv, though unlikely. Safe to keep index. But actually TMDB IDs are unique per type.
    media_type: str = Field(index=True) # 'movie' or 'tv'
    title: str
    poster_path: Optional[str] = None
    genres: Optional[str] = None # Stored as JSON string or comma separated
    origin_country: Optional[str] = None
    
    # New fields for stats
    runtime: Optional[int] = None # Minutes (Movie)
    number_of_episodes: Optional[int] = None # (TV)
    number_of_seasons: Optional[int] = None # (TV)
    cast: Optional[str] = None # Comma-separated list of main actors
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user_medias: List["UserMedia"] = Relationship(back_populates="media")

class UserMedia(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    media_id: int = Field(foreign_key="media.id", index=True)
    
    status: str = Field(default="watching") # watching, awaiting_episodes, finished, abandoned, watched
    rating: Optional[float] = None # 0-10
    comment: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship()
    media: Optional[Media] = Relationship(back_populates="user_medias")
    episode_activities: List["EpisodeActivity"] = Relationship(back_populates="user_media")

class EpisodeActivity(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("user_media_id", "season_number", "episode_number", name="unique_episode_activity"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_media_id: int = Field(foreign_key="usermedia.id", index=True)
    
    season_number: int
    episode_number: int
    
    rating: Optional[float] = None # 0-10
    comment: Optional[str] = None
    status: str = Field(default="watched") # watched, watching, skipped, etc.
    watched_at: datetime = Field(default_factory=datetime.utcnow)

    user_media: Optional[UserMedia] = Relationship(back_populates="episode_activities")
