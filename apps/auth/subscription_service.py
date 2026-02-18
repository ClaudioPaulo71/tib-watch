from typing import Optional
import stripe
from fastapi import Request
from sqlmodel import Session, select
from apps.auth.models import User
from config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class SubscriptionService:
    def __init__(self, session: Session):
        self.session = session

    def create_checkout_session(self, user: User, success_url: str, cancel_url: str) -> Optional[str]:
        if not settings.ENABLE_SUBSCRIPTION or not settings.STRIPE_PRICE_ID_PREMIUM:
            return None
            
        try:
            checkout_session = stripe.checkout.Session.create(
                customer_email=user.email,
                payment_method_types=['card'],
                line_items=[
                    {
                        'price': settings.STRIPE_PRICE_ID_PREMIUM,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(user.id)
            )
            return checkout_session.url
        except Exception as e:
            print(f"Stripe Error: {e}")
            return None

    def handle_webhook(self, payload: bytes, sig_header: str):
        if not settings.STRIPE_WEBHOOK_SECRET:
            return

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            raise ValueError("Invalid signature")

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self._fulfill_checkout(session)
            
        elif event['type'] == 'invoice.payment_succeeded':
             # Renovação bem sucedida
             pass
        elif event['type'] == 'invoice.payment_failed':
             # Falha no pagamento
             pass

    def _fulfill_checkout(self, session):
        user_id = session.get('client_reference_id')
        customer_id = session.get('customer')
        
        if user_id:
            user = self.session.get(User, int(user_id))
            if user:
                user.stripe_customer_id = customer_id
                user.subscription_status = 'active'
                self.session.add(user)
                self.session.commit()
