from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

class MediaType(str, Enum):
    MOVIE = "movie"
    TV = "tv"

class WatchStatus(str, Enum):
    PLAN_TO_WATCH = "plan_to_watch"
    WATCHING = "watching"
    COMPLETED = "completed"
    DROPPED = "dropped"
    WAITING_NEW_EPISODES = "waiting_new_episodes" # Specific for TV

class MediaItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tmdb_id: int = Field(index=True)
    media_type: MediaType
    title: str
    original_title: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = None
    genres: Optional[str] = None # Stored as comma-separated IDs or JSON string
    
    # Relationships
    watch_entries: List["WatchEntry"] = Relationship(back_populates="media_item")

# Reuse User from auth, but we need to define the relationship locally if we want ORM support
# For now, we'll link by user_id explicit field
    
class WatchEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True) # Linked to apps.auth.models.User.id
    media_item_id: int = Field(foreign_key="mediaitem.id")
    
    status: WatchStatus = Field(default=WatchStatus.PLAN_TO_WATCH)
    rating: Optional[int] = Field(default=None, ge=1, le=10) # 1-10
    general_comment: Optional[str] = None
    
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    media_item: MediaItem = Relationship(back_populates="watch_entries")
    episode_entries: List["EpisodeEntry"] = Relationship(back_populates="watch_entry")

class EpisodeEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    watch_entry_id: int = Field(foreign_key="watchentry.id")
    
    season_number: int
    episode_number: int
    title: Optional[str] = None
    
    rating: Optional[int] = Field(default=None, ge=1, le=10)
    comment: Optional[str] = None
    watched_at: datetime = Field(default_factory=datetime.utcnow)
    
    watch_entry: WatchEntry = Relationship(back_populates="episode_entries")
