from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlmodel import Session
from database import get_session
from apps.auth.subscription_service import SubscriptionService
from config import settings

router = APIRouter(prefix="/webhook", tags=["webhook"])

@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), session: Session = Depends(get_session)):
    if not settings.ENABLE_SUBSCRIPTION:
        return {"status": "ignored"}
        
    payload = await request.body()
    service = SubscriptionService(session)
    
    try:
        service.handle_webhook(payload, stripe_signature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return {"status": "success"}
