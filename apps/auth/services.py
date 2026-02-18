from typing import Optional, List
from sqlmodel import Session, select
from datetime import timedelta
from fastapi import Response, status, UploadFile
from fastapi.responses import RedirectResponse
import shutil
import uuid
from pathlib import Path

from apps.auth.models import User
from apps.auth.models import User
# from config import settings # Config not needed here anymore for token

from apps.core.base_service import BaseService

class AuthService(BaseService):

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.session.exec(select(User).where(User.email == email)).first()

    # Legacy methods (authenticate, register) removed. handled by Auth0 + Router logic now.
    # We keep profile management here.
    # --- PROFILE MANAGEMENT ---

    def update_profile(
        self, 
        user: User, 
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        profile_image: Optional[UploadFile] = None
    ) -> User:
        if full_name: user.full_name = full_name
        if phone: user.phone = phone
        if city: user.city = city
        if state: user.state = state
        if country: user.country = country
        
        if profile_image and profile_image.filename:
            # Reusing the logic from HumidorService - ideally this should be a shared utility
            extensao = profile_image.filename.split(".")[-1]
            nome_arquivo = f"user_{user.id}_{uuid.uuid4()}.{extensao}"
            caminho_destino = Path(f"static/uploads/profiles/{nome_arquivo}")
            caminho_destino.parent.mkdir(parents=True, exist_ok=True)
            
            with open(caminho_destino, "wb") as buffer:
                shutil.copyfileobj(profile_image.file, buffer)
            
            user.profile_image = str(caminho_destino)
            
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
