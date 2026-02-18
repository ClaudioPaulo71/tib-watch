import httpx
from typing import Optional, Dict, Any, List
from config import settings

class TMDBService:
    def __init__(self):
        self.api_key = settings.TMDB_API_KEY
        self.base_url = settings.TMDB_BASE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url, params={"api_key": self.api_key, "language": "en-US"})

    async def close(self):
        await self.client.aclose()

    async def search_multi(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search for movies and TV shows."""
        # Explicitly passing all params to ensure they are sent
        params = {
            "api_key": self.api_key,
            "language": "en-US",
            "query": query, 
            "page": page
        }
        response = await self.client.get("/search/multi", params=params)
        response.raise_for_status()
        return response.json()

    async def get_trending(self, media_type: str = "all", time_window: str = "week") -> Dict[str, Any]:
        """Get trending movies/tv shows."""
        response = await self.client.get(f"/trending/{media_type}/{time_window}")
        response.raise_for_status()
        return response.json()

    async def get_details(self, media_type: str, tmdb_id: int) -> Dict[str, Any]:
        """Get full details for a movie or TV show, including credits and keywords."""
        append_to = "credits,keywords" if media_type == 'movie' else "credits,keywords" # keywords endpoint slightly different for TV?
        # TMDB TV keywords are at /tv/{id}/keywords, but append_to_response works for 'keywords' too usually.
        # Actually for TV it might be 'keywords' or 'results' inside it.
        # Let's check TMDB API docs or just try. standard is append_to_response=keywords,credits
        
        response = await self.client.get(f"/{media_type}/{tmdb_id}", params={"append_to_response": "credits,keywords"})
        response.raise_for_status()
        return response.json()
    
    async def get_season_details(self, tv_id: int, season_number: int) -> Dict[str, Any]:
        """Get details for a specific season."""
        response = await self.client.get(f"/tv/{tv_id}/season/{season_number}")
        # Sometimes seasons like "Specials" (0) might not exist or yield 404 if not present in TMDB for some shows.
        # But generally it should return 404 if invalid. Raise status for now.
        if response.status_code == 404:
             return {}
        response.raise_for_status()
        return response.json()

    def get_image_url(self, path: Optional[str], size: str = "w500") -> Optional[str]:
        if not path:
            return None
        return f"https://image.tmdb.org/t/p/{size}{path}"
