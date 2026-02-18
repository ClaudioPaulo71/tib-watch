from fastapi import APIRouter, Depends, Form, Request, Response, status, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from database import get_session
from apps.auth.services import AuthService
from apps.auth.models import User
from apps.auth.subscription_service import SubscriptionService
from apps.tracker.services import TrackerService
# from apps.tracker.router import get_service # Hacky import removed

# Local dependency to avoid circular imports / context issues
def get_tracker_service(session: Session = Depends(get_session)) -> TrackerService:
    try:
        return TrackerService(session)
    except Exception as e:
        print(f"Error creating TrackerService: {e}")
        import traceback
        traceback.print_exc()
        raise e

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")

def get_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session)

from apps.auth.utils import oauth
import os

# --- AUTH0 ROUTES ---

@router.get("/login")
async def login(request: Request):
    if not oauth.auth0:
        return "Authentication service not configured"
    
    # Absolute URL for callback
    redirect_uri = request.url_for('auth_callback')
    return await oauth.auth0.authorize_redirect(request, redirect_uri)

@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, service: AuthService = Depends(get_service)):
    token = await oauth.auth0.authorize_access_token(request)
    user_info = token.get('userinfo')
    
    if not user_info:
        return "Failed to get user info"
        
    # User Info contains: sub, email, name, picture
    email = user_info.get('email')
    external_id = user_info.get('sub')
    picture = user_info.get('picture')
    name = user_info.get('name')
    
    # Get or Create User
    user = service.get_user_by_email(email)
    if not user:
        # Create new user
        # Password is not needed for external auth
        user = User(
            email=email, 
            external_id=external_id,
            full_name=name,
            profile_image=picture,
            is_active=True
        )
        service.session.add(user)
        service.session.commit()
        service.session.refresh(user)
    else:
        # Update existing user info if needed
        if not user.external_id:
            user.external_id = external_id
        if not user.profile_image:
            user.profile_image = picture
        service.session.add(user)
        service.session.commit()
        service.session.refresh(user)
    
    # Set Session
    request.session['user_id'] = user.id
    request.session['user_email'] = user.email
    request.session['user_image'] = user.profile_image or user.picture
    
    return RedirectResponse(url="/tracker/")

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    
    domain = os.getenv("AUTH0_DOMAIN")
    client_id = os.getenv("AUTH0_CLIENT_ID")
    
    # Auth0 Logout URL
    # https://YOUR_DOMAIN/v2/logout?client_id=YOUR_CLIENT_ID&returnTo=http://localhost:3000
    
    # Determine return URL (host root)
    return_to = str(request.base_url)
    
    logout_url = f"https://{domain}/v2/logout?client_id={client_id}&returnTo={return_to}"
    return RedirectResponse(url=logout_url)

# Legacy Register (Disabled/Redirect to Login)
@router.get("/register")
def register_page():
    return RedirectResponse(url="/auth/login")

@router.post("/register")
def register():
    return RedirectResponse(url="/auth/login")

from apps.auth.subscription_service import SubscriptionService
from apps.auth.deps import get_current_user, require_user
from apps.tracker.services import TrackerService # Added import for TrackerService

# --- PROFILE ROUTES ---

@router.get("/profile")
def profile(
    request: Request, 
    user: User = Depends(get_current_user),
    service: TrackerService = Depends(get_tracker_service) # Inject tracker service for stats
):
    if not user:
         return RedirectResponse(url="/auth/login")
         
    try:
        # Fetch stats for the credential
        stats = service.get_dashboard_stats(user.id)
        # vCard Generation
        import urllib.parse
        vcard = f"BEGIN:VCARD\nVERSION:3.0\nFN:{user.full_name}\nEMAIL:{user.email}\nTEL:{user.phone or ''}\nADR:;;;{user.city or ''};{user.state or ''};;;\nEND:VCARD"
        vcard_encoded = urllib.parse.quote(vcard)

        return templates.TemplateResponse("auth/profile_credential.html", {
            "request": request, 
            "user": user,
            "stats": stats,
            "vcard_data": vcard_encoded
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error: {e}"

@router.get("/profile/edit")
def edit_profile_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("auth/profile_edit.html", {
        "request": request,
        "user": user
    })

@router.post("/profile")
def update_profile(
    request: Request,
    full_name: str = Form(default=None),
    phone: str = Form(default=None),
    city: str = Form(default=None),
    state: str = Form(default=None),
    country: str = Form(default=None),
    profile_image: UploadFile = File(default=None),
    service: AuthService = Depends(get_service),
    user: User = Depends(require_user)
):
    updated_user = service.update_profile(user, full_name, phone, city, state, country, profile_image)
    
    # Update Session with new image if changed
    if updated_user.profile_image:
        request.session['user_image'] = updated_user.profile_image
        
    return RedirectResponse(url="/auth/profile", status_code=303)

@router.get("/subscribe")
def subscribe_premium(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    sub_service = SubscriptionService(session)
    success_url = str(request.url_for('listar_veiculos')) # Redirect to home
    cancel_url = str(request.url_for('listar_veiculos'))
    
    checkout_url = sub_service.create_checkout_session(user, success_url, cancel_url)
    
    if checkout_url:
        return RedirectResponse(checkout_url, status_code=303)
    
    return RedirectResponse("/analytics?error=payment_config_missing", status_code=303) 

