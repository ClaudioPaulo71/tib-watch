from fastapi import APIRouter, Depends, Request, Form, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from apps.core.tmdb import TMDBService
from apps.tracker.services import TrackerService
from database import get_session
from sqlmodel import Session
from apps.auth.deps import get_current_user, require_user
from apps.auth.models import User
import json

router = APIRouter(prefix="/tracker", tags=["tracker"])
templates = Jinja2Templates(directory="templates")

async def run_sync_task(user_id: int, tmdb_id: int, status: str, rating: float = None):
    """
    Background task to sync episodes.
    Creates its own session to avoid "Session is closed" errors.
    """
    from database import engine
    from sqlmodel import Session
    
    # Create a fresh session for the background task
    with Session(engine) as session:
        service = TrackerService(session)
        try:
            await service.sync_series_episodes_activity(user_id, tmdb_id, status, rating)
        except Exception as e:
            print(f"[ERROR] Background Sync Failed: {e}")
        finally:
            # Must close the TMDB client manually as it's created in __init__
            await service.tmdb.close()

def get_service(session: Session = Depends(get_session)) -> TrackerService:
    return TrackerService(session)

@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: User = Depends(require_user),
    service: TrackerService = Depends(get_service)
):
    try:
        stats = service.get_dashboard_stats(user.id)
        return templates.TemplateResponse("tracker/dashboard.html", {
            "request": request, 
            "stats": stats,
            "user": user,
            "page_title": "All Activity"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error: {e}"

@router.get("/movies", response_class=HTMLResponse)
@router.get("/movies", response_class=HTMLResponse)
def dashboard_movies(
    request: Request,
    user: User = Depends(require_user),
    service: TrackerService = Depends(get_service)
):
    stats = service.get_dashboard_stats(user.id, media_type_filter="movie")
    return templates.TemplateResponse("tracker/dashboard.html", {
        "request": request, 
        "stats": stats,
        "user": user,
        "page_title": "Movies"
    })

@router.get("/tv", response_class=HTMLResponse)
def dashboard_tv(
    request: Request,
    user: User = Depends(require_user),
    service: TrackerService = Depends(get_service)
):
    stats = service.get_dashboard_stats(user.id, media_type_filter="tv")
    return templates.TemplateResponse("tracker/dashboard.html", {
        "request": request, 
        "stats": stats,
        "user": user,
        "page_title": "TV Shows"
    })

@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("tracker/search.html", {"request": request})

@router.get("/search/results", response_class=HTMLResponse)
async def search_results(request: Request, q: str):
    if not q:
        return ""
        
    print(f"DEBUG: Search query received: '{q}'")
    service = TMDBService()
    try:
        data = await service.search_multi(q)
        # print(f"DEBUG: Raw TMDB Response: {data}")
        results = data.get("results", [])
        print(f"DEBUG: Found {len(results)} results for '{q}'")
    except Exception as e:
        print(f"Search Error: {e}")
        import traceback
        traceback.print_exc()
        results = []
    finally:
        await service.close()
        
    return templates.TemplateResponse("tracker/partials_search_results.html", {"request": request, "results": results})

@router.get("/details/{media_type}/{tmdb_id}", response_class=HTMLResponse)
async def media_details(
    request: Request, 
    media_type: str, 
    tmdb_id: int, 
    service: TrackerService = Depends(get_service)
):
    user_id = request.session.get('user_id')
    # Fetch details even if user not logged in (will show generic view)
    # But for 'in_list' status, we need user_id
    
    context_data = await service.get_details_context(user_id, media_type, tmdb_id)
    
    return templates.TemplateResponse("tracker/details.html", {
        "request": request, 
        "media": context_data['media'],
        "media_type": media_type, # Explicitly pass media_type
        "user_status": context_data['user_status'],
        "user_rating": context_data.get('user_rating'), # Pass rating explicitly
        "user_comment": context_data.get('user_comment'), # Ensure comment is passed too
        "in_list": context_data['in_list'],
        "series_stats": context_data.get('series_stats') # Ensure series stats are passed too just in case
    })

@router.post("/add")
async def add_media(
    request: Request,
    media_type: str = Form(...),
    tmdb_id: int = Form(...),
    status: str = Form(...),
    title: str = Form(...),
    poster_path: str = Form(None),
    genres: str = Form(None), # Comma separated from frontend
    runtime: int = Form(0),
    number_of_episodes: int = Form(0),
    background_tasks: BackgroundTasks = None,
    service: TrackerService = Depends(get_service),
    user: User = Depends(require_user)
):
    # Fetch full details from TMDB to ensure we have cast, runtime, seasons etc.
    try:
        tmdb_service = TMDBService()
        media_data = await tmdb_service.get_details(media_type, tmdb_id)
        await tmdb_service.close()
    except Exception as e:
        print(f"Error fetching details in add_media: {e}")
        # Fallback to form data if fetch fails
        media_data = {
            "id": tmdb_id,
            "media_type": media_type,
            "title": title,
            "poster_path": poster_path,
            "genres": [{"name": g.strip()} for g in genres.split(',')] if genres else [],
            "origin_country": [], 
            "runtime": runtime,
            "number_of_episodes": number_of_episodes
        }
    
    service.update_status(user, media_data, status)
    
    # Sync episodes if TV and status is watched/finished
    if media_type == 'tv' and status in ['watched', 'finished']:
         background_tasks.add_task(run_sync_task, user.id, tmdb_id, status)
    
    # Return updated partial for the button region
    return templates.TemplateResponse("tracker/partials_action_buttons.html", {
        "request": request,
        "media": { # Construct minimal context for template
             "id": tmdb_id, # TMDB ID
             "media_type": media_type
        },
        "user_status": status,
        "in_list": True
    })

@router.get("/review/{media_type}/{tmdb_id}")
async def review_modal_form(
    request: Request, 
    media_type: str, 
    tmdb_id: int,
    service: TrackerService = Depends(get_service)
):
    user_id = request.session.get('user_id')
    context = await service.get_details_context(user_id, media_type, tmdb_id)
    
    if not context['in_list']:
         # Fallback: maybe just show empty form? But semantics imply editing an existing entry usually.
         # For now, let's assume valid flow.
         pass
        
    return templates.TemplateResponse("tracker/partials_review_modal.html", {
        "request": request,
        "media": context['media'],
        "media_type": media_type, # Pass explicitly for form action
        "user_media": {
            "status": context['user_status'],
            "rating": context['user_rating'],
            "comment": context['user_comment']
        }
    })

@router.post("/review/{media_type}/{tmdb_id}")
async def submit_review(
    request: Request,
    media_type: str,
    tmdb_id: int,
    status: str = Form(...),
    rating: float = Form(...),
    comment: str = Form(""),
    background_tasks: BackgroundTasks = None,
    user: User = Depends(require_user),
    service: TrackerService = Depends(get_service)
):
    # We need to find the Media ID from TMDB ID
    # Service update_review expects media_id (DB ID).
    # Let's helper method in service to resolve or just look it up here.
    
    # Better: Update update_review to accept TMDB ID + Type and resolve internally, 
    # OR resolve here.
    
    # Resolving UserMedia to get ID
    # Actually service.update_review logic takes user_id and media_id.
    
    # Reuse service.get_details_context logic to find media? Too heavy.
    # Reuse update_status logic?
    
    # Let's add a method to service: update_review_by_tmdb
    
    # For now, let's quick fix by fetching media first.
    from sqlmodel import select
    from apps.tracker.models import Media
    
    media = service.session.exec(
        select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == media_type)
    ).first()
    
    if media:
        service.update_review(user.id, media.id, status, rating, comment)

        # Sync episodes if TV and status is watched/finished
        if media.media_type == 'tv' and status in ['watched', 'finished']:
             background_tasks.add_task(run_sync_task, user.id, media.tmdb_id, status, rating)
    
    # Return updated buttons
    response = templates.TemplateResponse("tracker/partials_action_buttons.html", {
        "request": request,
        "media": {"id": tmdb_id, "media_type": media_type},
        "user_status": status,
        "in_list": True
    })
    
    # Always refresh to ensure main page stats update
    response.headers['HX-Refresh'] = "true"
         
    return response

@router.delete("/media/{media_type}/{tmdb_id}")
async def remove_media(
    request: Request,
    media_type: str,
    tmdb_id: int,
    user: User = Depends(require_user),
    service: TrackerService = Depends(get_service)
):
    success = service.remove_user_media(user.id, tmdb_id, media_type)
    
    if success:
        # Redirect to dashboard or search?
        # Since this likely called from details page modal, we should probably redirect to dashboard 
        # or refresh page (which would show "Add to List" button).
        
        # Redirect to dashboard to show updated list
        response = Response(status_code=200)
        response.headers['HX-Redirect'] = "/tracker/"
        return response
    else:
        return Response(status_code=404)

# --- TV Show Season & Episodes ---

@router.get("/partials/season/{tmdb_id}/{season_number}", response_class=HTMLResponse)
async def get_season_episodes(
    request: Request,
    tmdb_id: int,
    season_number: int,
    service: TrackerService = Depends(get_service)
):
    user_id = request.session.get('user_id')
    context = await service.get_season_context(user_id, tmdb_id, season_number)
    
    return templates.TemplateResponse("tracker/partials_season_episodes.html", {
        "request": request,
        "tmdb_id": tmdb_id,
        "season_number": season_number, # Explicitly pass season_number
        "season": context['season_data'],
        "episodes": context['episodes']
    })

@router.post("/api/episode/{tmdb_id}/{season_number}/{episode_number}")
async def update_episode_activity(
    request: Request,
    tmdb_id: int,
    season_number: int,
    episode_number: int,
    action: str = Form(...), # watch, unwatch, rate, comment
    rating: float = Form(None),
    comment: str = Form(None),
    user: User = Depends(require_user),
    service: TrackerService = Depends(get_service)
):
    activity = service.update_episode_activity(
        user.id, tmdb_id, season_number, episode_number, action, rating, comment
    )
    
    # We need to return the updated partial for this specific episode card
    # Ideally we'd just re-render the card. 
    # But wait, we need the episode details from TMDB to re-render the card fully?
    # Or just return the "user_activity" part?
    
    # Let's re-fetch just the specific episode context? Or constructing it manually if heavy.
    # Re-fetching season context is heavy.
    
    # Let's TRY to construct the context for the template manually using what we have + Form data?
    # Or just fetch the episode details again?
    
    # Let's fetch the specific episode using TMDBService just to be safe and clean.
    # It adds latency but ensures correctness.
    
    # Actually, we can just return a "success" or minimal partial if the UI handles it.
    # But HTMX usually swaps content.
    
    # Let's fetch season context again? It's easiest but slower. 
    # Optimization: We only need this one episode.
    # But get_season_context fetches the whole season.
    
    # Let's fetch just the one episode details from TMDB?
    # Or do we strictly need TMDB data for the card? Yes, for title/overview/image.
    
    # Let's use get_season_context for now. Robustness first.
    context = await service.get_season_context(user.id, tmdb_id, season_number)
    
    # Find the specific episode in the list
    target_ep = next((ep for ep in context['episodes'] if ep['tmdb']['episode_number'] == episode_number), None)
    
    if not target_ep:
        return "Error: Episode not found"
        
    return templates.TemplateResponse("tracker/partials_season_episodes_card.html", {
        "request": request,
        "tmdb_id": tmdb_id,
        "season_number": season_number,
        "episode": target_ep
    })
