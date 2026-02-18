from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from apps.tracker.models import Media, UserMedia, EpisodeActivity
from apps.auth.models import User
from apps.core.tmdb import TMDBService
from starlette.concurrency import run_in_threadpool

class TrackerService:
    def __init__(self, session: Session):
        self.session = session
        self.tmdb = TMDBService()

    async def get_details_context(self, user_id: int, media_type: str, tmdb_id: int) -> Dict[str, Any]:
        """
        Fetches full details from TMDB and checks the user's tracking status.
        """
        # 1. Fetch from TMDB
        try:
            tmdb_data = await self.tmdb.get_details(media_type, tmdb_id)
        finally:
            await self.tmdb.close()

        # 2. Check localized DB Status
        user_media = None
        media = self.session.exec(
            select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == media_type)
        ).first()

        if media:
            user_media = self.session.exec(
                select(UserMedia).where(UserMedia.user_id == user_id, UserMedia.media_id == media.id)
            ).first()

        # 3. Get Stats for TV
        series_stats = None
        if media_type == 'tv':
            series_stats = self.get_series_watch_stats(user_id, tmdb_id)

        return {
            "media": tmdb_data,
            "user_status": user_media.status if user_media else None,
            "user_rating": user_media.rating if user_media else None,
            "user_comment": user_media.comment if user_media else None,
            "in_list": user_media is not None,
            "series_stats": series_stats
        }

    async def get_season_context(self, user_id: int, tmdb_id: int, season_number: int) -> Dict[str, Any]:
        """
        Fetches full season details from TMDB and merges with User's EpisodeActivity.
        """
        # 1. Fetch Season from TMDB
        try:
            season_data = await self.tmdb.get_season_details(tmdb_id, season_number)
        except Exception as e:
            print(f"Error fetching season {season_number}: {e}")
            season_data = {}

        episodes = season_data.get("episodes", [])
        
        # 2. Fetch User Activity if logged in
        episode_map = {}
        if user_id:
            # We need the UserMedia ID first
            media = self.session.exec(
                select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == 'tv')
            ).first()

            if media:
                user_media = self.session.exec(
                    select(UserMedia).where(UserMedia.user_id == user_id, UserMedia.media_id == media.id)
                ).first()
                
                if user_media:
                    # Fetch all activities for this season
                    activities = self.session.exec(
                        select(EpisodeActivity).where(
                            EpisodeActivity.user_media_id == user_media.id,
                            EpisodeActivity.season_number == season_number
                        )
                    ).all()
                    
                    for act in activities:
                        episode_map[act.episode_number] = act

        # 3. Merge Data
        processed_episodes = []
        for ep in episodes:
            ep_num = ep.get("episode_number")
            activity = episode_map.get(ep_num)
            
            processed_episodes.append({
                "tmdb": ep,
                "user_activity": {
                    "rating": activity.rating if activity else None,
                    "comment": activity.comment if activity else None,
                    "status": activity.status if activity else None,
                    "watched": True if activity and activity.status == 'watched' else False 
                }
            })
            
        return {
            "season_data": season_data,
            "episodes": processed_episodes
        }

    def update_status(self, user: User, media_data: Dict[str, Any], status: str) -> UserMedia:
        """
        Create or Update Media and UserMedia entries.
        """
        tmdb_id = media_data.get("id")
        media_type = media_data.get("media_type", "movie") # Default fallback, though should be explicit
        
        # 1. Ensure Media Exists
        media = self.session.exec(
            select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == media_type)
        ).first()

        if not media:
            # Create Media Cache
            genres = ",".join([g['name'] for g in media_data.get('genres', [])])
            origin = media_data.get('origin_country', [])
            origin_str = origin[0] if origin else None
            
            title = media_data.get("title") or media_data.get("name")
            
            # Extract Cast
            credits = media_data.get("credits", {})
            cast_list = credits.get("cast", [])
            cast_str = ",".join([c['name'] for c in cast_list[:5]]) if cast_list else None

            media = Media(
                tmdb_id=tmdb_id,
                media_type=media_type,
                title=title,
                poster_path=media_data.get("poster_path"),
                genres=genres,
                origin_country=origin_str,
                runtime=media_data.get("runtime"),
                number_of_episodes=media_data.get("number_of_episodes"),
                number_of_seasons=media_data.get("number_of_seasons"),
                cast=cast_str
            )
            self.session.add(media)
            self.session.commit()
            self.session.refresh(media)

        # 2. Update User Tracking
        user_media = self.session.exec(
            select(UserMedia).where(UserMedia.user_id == user.id, UserMedia.media_id == media.id)
        ).first()

        if not user_media:
            user_media = UserMedia(
                user_id=user.id,
                media_id=media.id,
                status=status
            )
        else:
            user_media.status = status
            user_media.updated_at = datetime.utcnow()
        
        self.session.add(user_media)
        self.session.commit()
        self.session.refresh(user_media)
        
        return user_media

    def get_user_media(self, user_id: int, media_id: int) -> Optional[UserMedia]:
        return self.session.exec(
            select(UserMedia).where(UserMedia.user_id == user_id, UserMedia.media_id == media_id)
        ).first()

    def update_review(self, user_id: int, media_id: int, status: str, rating: float, comment: str) -> UserMedia:
        user_media = self.get_user_media(user_id, media_id)
        if user_media:
            user_media.status = status
            user_media.rating = rating
            user_media.comment = comment
            user_media.updated_at = datetime.utcnow()
            
            self.session.add(user_media)
            self.session.commit()
            self.session.refresh(user_media)
            
        return user_media

    def remove_user_media(self, user_id: int, tmdb_id: int, media_type: str) -> bool:
        """
        Removes a movie/show from the user's list.
        """
        # 1. Find the Media
        media = self.session.exec(
            select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == media_type)
        ).first()

        if not media:
            return False

        # 2. Find the UserMedia
        user_media = self.session.exec(
            select(UserMedia).where(UserMedia.user_id == user_id, UserMedia.media_id == media.id)
        ).first()

        if user_media:
            # 3. Optional: Delete associated EpisodeActivity if any?
            # For now, let's keep it simple and just delete UserMedia. 
            # Cascade delete should handle activities if configured, otherwise we might leave orphans.
            # Let's check models.py later. For now, manual cleanup might be safer if not cascaded.
            
            # Delete UserMedia
            self.session.delete(user_media)
            self.session.commit()
            return True
        
        return False

    def update_episode_activity(self, user_id: int, tmdb_id: int, season_number: int, episode_number: int, 
                              action: str, rating: float = None, comment: str = None) -> Optional[EpisodeActivity]:
        """
        Update episode activity (watch, rate, comment).
        Action: 'watch', 'unwatch', 'rate', 'comment' 
        """
        from sqlalchemy.exc import IntegrityError
        print(f"[DEBUG] update_episode_activity: user={user_id}, tmdb={tmdb_id}, S{season_number}E{episode_number}, action={action}")

        # 1. Ensure Media Exists (it should if we are here, but double check)
        media = self.session.exec(
            select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == 'tv')
        ).first()

        if not media:
            try:
                media = Media(tmdb_id=tmdb_id, media_type='tv', title=f"TV Show {tmdb_id}")
                self.session.add(media)
                self.session.commit()
                self.session.refresh(media)
            except IntegrityError:
                self.session.rollback()
                media = self.session.exec(
                    select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == 'tv')
                ).first()

        # 2. Ensure UserMedia Exists
        user_media = self.session.exec(
            select(UserMedia).where(UserMedia.user_id == user_id, UserMedia.media_id == media.id)
        ).first()

        if not user_media:
            try:
                user_media = UserMedia(user_id=user_id, media_id=media.id, status="watching")
                self.session.add(user_media)
                self.session.commit()
                self.session.refresh(user_media)
            except IntegrityError:
                self.session.rollback()
                user_media = self.session.exec(
                    select(UserMedia).where(UserMedia.user_id == user_id, UserMedia.media_id == media.id)
                ).first()

        # 3. Find/Create Activity with Retry Logic
        for attempt in range(3):
            try:
                activity = self.session.exec(
                    select(EpisodeActivity).where(
                        EpisodeActivity.user_media_id == user_media.id,
                        EpisodeActivity.season_number == season_number,
                        EpisodeActivity.episode_number == episode_number
                    )
                ).first()

                if action == 'unwatch':
                    if activity:
                        self.session.delete(activity)
                        self.session.commit()
                    return None

                if not activity:
                    activity = EpisodeActivity(
                        user_media_id=user_media.id,
                        season_number=season_number,
                        episode_number=episode_number,
                        status="watched" 
                    )
                    self.session.add(activity)

                # Update fields based on action
                if action == 'rate':
                    activity.rating = rating
                elif action == 'comment':
                    activity.comment = comment
                elif action in ['watched', 'watching', 'skipped', 'wishlist']:
                    activity.status = action
                
                self.session.add(activity)
                self.session.commit()
                self.session.refresh(activity)
                return activity
            except IntegrityError:
                self.session.rollback()
                continue
            except Exception as e:
                print(f"[ERROR] update_episode_activity error: {e}")
                self.session.rollback()
                raise e
        
        raise Exception("Failed to update episode activity due to concurrency")

    async def sync_series_episodes_activity(self, user_id: int, tmdb_id: int, status: str, rating: float = None) -> None:
        """
        If status is 'watched' or 'finished', mark all episodes as watched.
        This fetches all seasons and episodes from TMDB and updates them.
        """
        if status not in ['watched', 'finished']:
            return

        print(f"[INFO] Syncing episodes for Series {tmdb_id} (Status: {status})")

        # 1. Fetch Series Details to get Season Count
        try:
            series_data = await self.tmdb.get_details('tv', tmdb_id)
        except Exception as e:
            print(f"[ERROR] Sync failed: Could not fetch series details ({e})")
            return

        seasons = series_data.get('seasons', [])
        
        # 2. Iterate Seasons
        for season in seasons:
            season_number = season.get('season_number')
            
            # Skip Season 0 (Specials) if that's preferred, but usually 'Watched' implies everything.
            # Let's include everything for now.
            
            # Fetch Season Details (to get episodes)
            try:
                # We need to await this as it is async in TMDBService
                season_details = await self.tmdb.get_season_details(tmdb_id, season_number)
            except Exception as e:
                print(f"[ERROR] Sync season {season_number} failed: {e}")
                continue
                
            episodes = season_details.get('episodes', [])
            
            # 3. Mark Episodes
            for episode in episodes:
                ep_num = episode.get('episode_number')
                try:
                    # 1. Mark as Watched
                    await run_in_threadpool(
                        self.update_episode_activity,
                        user_id, tmdb_id, season_number, ep_num, 
                        action='watched'
                    )
                    
                    # 2. Apply Rating if provided
                    if rating is not None:
                        await run_in_threadpool(
                            self.update_episode_activity,
                            user_id, tmdb_id, season_number, ep_num, 
                            action='rate', rating=rating
                        )
                        
                except Exception as e:
                    print(f"[ERROR] Failed to sync episode S{season_number}E{ep_num}: {e}")
        
        print(f"[INFO] Completed episode sync for Series {tmdb_id}")
    def get_series_watch_stats(self, user_id: int, tmdb_id: int) -> Dict[str, Any]:
        """
        Calculates time watched for a specific series.
        """
        # 1. Get Media
        media = self.session.exec(
            select(Media).where(Media.tmdb_id == tmdb_id, Media.media_type == 'tv')
        ).first()
        
        if not media:
            return {"episodes_watched": 0, "total_minutes": 0, "time_str": "0h"}
            
        # 2. Get UserMedia
        user_media = self.session.exec(
            select(UserMedia).where(UserMedia.user_id == user_id, UserMedia.media_id == media.id)
        ).first()
        
        if not user_media:
            return {"episodes_watched": 0, "total_minutes": 0, "time_str": "0h"}
            
        # 3. Count Watched Episodes
        # We count episodes with status 'watched'
        # We could also count 'watching' as partial? For now let's just count 'watched'.
        activities = self.session.exec(
            select(EpisodeActivity).where(
                EpisodeActivity.user_media_id == user_media.id,
                EpisodeActivity.status == 'watched'
            )
        ).all()
        
        count = len(activities)
        runtime = media.runtime or 0
        if runtime == 0: runtime = 45 # Default fallback
        
        total_minutes = count * runtime
        total_hours = round(total_minutes / 60, 1)
        
        return {
            "episodes_watched": count, 
            "total_minutes": total_minutes, 
            "time_str": f"{total_hours}h"
        }

    def get_dashboard_stats(self, user_id: int, media_type_filter: Optional[str] = None) -> Dict[str, Any]:
        # 1. Fetch all user media with media details
        query = select(UserMedia, Media).join(Media).where(UserMedia.user_id == user_id)
        
        if media_type_filter:
            query = query.where(Media.media_type == media_type_filter)
            
        results = self.session.exec(query).all()
        
        # 2. Fetch all episode activities for this user to avoid N+1
        # 2. Fetch all episode activities for this user to avoid N+1
        from sqlmodel import func
        
        act_query = select(EpisodeActivity.user_media_id, func.count(EpisodeActivity.id)).join(UserMedia).where(
            UserMedia.user_id == user_id, 
            EpisodeActivity.status == 'watched'
        ).group_by(EpisodeActivity.user_media_id)
        
        activity_counts = dict(self.session.exec(act_query).all()) # {user_media_id: count}
        
        total_titles = len(results)
        movies_watched = 0
        series_finished = 0
        total_minutes = 0
        
        # New structure for specific grouping
        movies_by_status = {}
        tv_by_status = {}

        recent_activity = []
        
        for user_media, media in results:
            # Stats Calculation
            runtime = media.runtime or 0
            
            # Estimate runtime if missing
            if runtime == 0:
                if media.media_type == 'movie': runtime = 120
                elif media.media_type == 'tv': runtime = 45

            if media.media_type == 'movie':
                # Count if watched OR watching (users might be imprecise)
                if user_media.status in ['watched', 'managed', 'finished']:
                    movies_watched += 1
                    total_minutes += runtime
                
                # Grouping
                if user_media.status not in movies_by_status: movies_by_status[user_media.status] = []
                movies_by_status[user_media.status].append({
                    "media": media,
                    "user_media": user_media
                })

            elif media.media_type == 'tv':
                if user_media.status in ['finished', 'watched']:
                    series_finished += 1
                
                # Use accurate count from activities
                watched_count = activity_counts.get(user_media.id, 0)
                if watched_count > 0:
                    total_minutes += (runtime * watched_count)
                elif user_media.status in ['finished', 'watched']:
                    # Fallback if no specific episodes marked but show is marked finished
                    ep_count = media.number_of_episodes or 10
                    total_minutes += (runtime * ep_count)

                # Grouping
                if user_media.status not in tv_by_status: tv_by_status[user_media.status] = []
                tv_by_status[user_media.status].append({
                    "media": media,
                    "user_media": user_media
                })
            
        # Sort lists by updated_at desc
        for status_list in movies_by_status.values():
            status_list.sort(key=lambda x: x['user_media'].updated_at, reverse=True)
            
        for status_list in tv_by_status.values():
            status_list.sort(key=lambda x: x['user_media'].updated_at, reverse=True)
        
        # Convert minutes to Hours/Days
        total_hours = int(total_minutes / 60)
        total_days = round(total_hours / 24, 1)
        
        return {
            "total_titles": total_titles,
            "movies_watched": movies_watched,
            "series_finished": series_finished,
            "total_minutes": total_minutes,
            "total_hours": total_hours,
            "total_days": total_days,
            
            "movies_by_status": movies_by_status,
            "tv_by_status": tv_by_status,
            
            "filter": media_type_filter
        }
