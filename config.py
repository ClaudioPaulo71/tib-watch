import os
from dotenv import load_dotenv
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "TIB Watch"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "watch_secret_key_123")
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/tib_watch.db")
    
    # TMDB
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_URL: str = "https://image.tmdb.org/t/p/w500" # Common size
    
    # Auth0
    AUTH0_DOMAIN: Optional[str] = os.getenv("AUTH0_DOMAIN")
    AUTH0_CLIENT_ID: Optional[str] = os.getenv("AUTH0_CLIENT_ID")
    AUTH0_CLIENT_SECRET: Optional[str] = os.getenv("AUTH0_CLIENT_SECRET")
    AUTH0_CALLBACK_URL: str = os.getenv("AUTH0_CALLBACK_URL", "https://watch.tib-usa.app/auth/callback")
    
    # Monetization
    ENABLE_SUBSCRIPTION: bool = False
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PRICE_ID_PREMIUM: Optional[str] = os.getenv("STRIPE_PRICE_ID_PREMIUM")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
