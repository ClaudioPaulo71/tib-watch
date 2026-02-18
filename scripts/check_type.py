from sqlmodel import Session, select, create_engine
from apps.tracker.models import Media

# Connect to the database
engine = create_engine("sqlite:///data/tib_watch.db")

def check_media_types():
    with Session(engine) as session:
        # Get last 10 media items
        media_items = session.exec(select(Media).order_by(Media.id.desc()).limit(10)).all()
        
        print(f"{'ID':<5} {'Type':<10} {'Title':<40} {'TMDB ID'}")
        print("-" * 70)
        for m in media_items:
            print(f"{m.id:<5} {m.media_type:<10} {m.title[:38]:<40} {m.tmdb_id}")

if __name__ == "__main__":
    check_media_types()
