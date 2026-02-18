from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, date

if TYPE_CHECKING:
    from apps.garage.models import Veiculo

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: Optional[str] = None
    external_id: Optional[str] = Field(default=None, index=True) # Auth0 Sub ID
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Profile Fields
    full_name: Optional[str] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    profile_image: Optional[str] = None # URL to uploaded photo
    
    # Monetization
    stripe_customer_id: Optional[str] = None
    subscription_status: str = Field(default="free") # free, active, past_due, canceled
    subscription_end_date: Optional[date] = None

    # veiculos: List["Veiculo"] = Relationship(back_populates="user")
