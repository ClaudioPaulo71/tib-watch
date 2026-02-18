from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
import os
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from database import create_db_and_tables
from apps.auth.router import router as auth_router
from apps.tracker.router import router as tracker_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="TIB Watch", lifespan=lifespan)

# Middlewares
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
from config import settings
# Use settings.SECRET_KEY to ensure consistency
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, https_only=False, same_site="lax")

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Routers
app.include_router(auth_router)
app.include_router(tracker_router)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # If user is logged in, you might still want to show landing page 
    # but with "Go to Dashboard" button (handled in template)
    # OR redirect them straight to tracker?
    # Usually SaaS apps show landing page at root even if logged in, 
    # or redirect to /dashboard if logged in. 
    # Let's show Landing Page for everyone, template handles the button state.
    
    return templates.TemplateResponse("landing.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
