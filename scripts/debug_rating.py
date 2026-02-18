from sqlmodel import Session, select
from database import engine
from apps.auth.models import User
from apps.tracker.models import Media, UserMedia

def debug_ratings():
    with Session(engine) as session:
        # Get user (assuming first user or specific email if known)
        user = session.exec(select(User)).first()
        if not user:
            print("No user found.")
            return

        print(f"Checking ratings for User: {user.email} (ID: {user.id})")
        
        # Get all UserMedia with ratings or comments
        user_medias = session.exec(
            select(UserMedia).where(UserMedia.user_id == user.id)
        ).all()
        
        print(f"Found {len(user_medias)} UserMedia records.")
        
        for um in user_medias:
            media = session.get(Media, um.media_id)
            print(f"- Media: {media.title if media else 'Unknown'} (TMDB: {media.tmdb_id if media else '?'})")
            print(f"  Status: {um.status}")
            print(f"  Rating: {um.rating}")
            print(f"  Comment: {um.comment}")
            print("-" * 30)

if __name__ == "__main__":
    debug_ratings()
