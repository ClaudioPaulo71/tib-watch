import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

async def test_search():
    print(f"Testing TMDB API with Key: {API_KEY[:5]}...{API_KEY[-5:] if API_KEY else 'None'}")
    
    if not API_KEY:
        print("ERROR: TMDB_API_KEY is missing!")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/search/multi",
                params={"api_key": API_KEY, "query": "Inception", "page": 1}
            )
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"Success! Found {len(results)} results.")
                if results:
                    print(f"First result: {results[0].get('title') or results[0].get('name')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
