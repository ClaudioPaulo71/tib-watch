from sqlmodel import Session, select, func
from database import engine
from apps.tracker.models import EpisodeActivity

def check_duplicates():
    with Session(engine) as session:
        # Check for duplicates: Group by (user_media_id, season_number, episode_number) -> count > 1
        query = select(
            EpisodeActivity.user_media_id, 
            EpisodeActivity.season_number, 
            EpisodeActivity.episode_number,
            func.count(EpisodeActivity.id)
        ).group_by(
            EpisodeActivity.user_media_id, 
            EpisodeActivity.season_number, 
            EpisodeActivity.episode_number
        ).having(func.count(EpisodeActivity.id) > 1)
        
        results = session.exec(query).all()
        
        if results:
            print(f"FOUND {len(results)} DUPLICATE GROUPS:")
            for row in results:
                print(f"UserMedia: {row[0]}, S{row[1]}E{row[2]}, Count: {row[3]}")
                
            # Optional: Show the actual IDs
            # user_media = 1, s=1, e=2
            # session.exec(select(EpisodeActivity)...)
        else:
            print("No duplicates found.")

if __name__ == "__main__":
    check_duplicates()
