"""
Analytics module for tracking user interactions
Stores impressions and engagement data in S3
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.s3_storage import S3Storage


class AnalyticsTracker:
    """Track user analytics and engagement"""

    def __init__(self, s3_storage: S3Storage):
        self.s3_storage = s3_storage

    async def track_impression(
        self,
        user_id: str,
        activity_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track an impression (view) of an activity

        Args:
            user_id: User who viewed the activity
            activity_id: Activity that was viewed
            metadata: Additional metadata (duration, scroll depth, etc.)

        Returns:
            Success status
        """
        try:
            # Load user's impression history
            user_key = f"analytics/impressions_{user_id}.json"
            data = await self.s3_storage.read(user_key) or {'impressions': {}}

            # Track this impression
            if activity_id not in data['impressions']:
                data['impressions'][activity_id] = {
                    'first_viewed_at': datetime.utcnow().isoformat(),
                    'view_count': 0,
                    'last_viewed_at': None
                }

            impression = data['impressions'][activity_id]
            impression['view_count'] += 1
            impression['last_viewed_at'] = datetime.utcnow().isoformat()

            if metadata:
                impression['metadata'] = metadata

            # Save updated impressions
            await self.s3_storage.write(user_key, data)

            return True

        except Exception as e:
            print(f"❌ Failed to track impression: {str(e)}")
            return False

    async def get_user_impressions(self, user_id: str) -> Dict[str, Any]:
        """
        Get all impressions for a user

        Args:
            user_id: User ID

        Returns:
            User's impression data
        """
        try:
            user_key = f"analytics/impressions_{user_id}.json"
            data = await self.s3_storage.read(user_key) or {'impressions': {}}
            return data
        except Exception as e:
            print(f"❌ Failed to get impressions: {str(e)}")
            return {'impressions': {}}

    async def get_activity_stats(self, activity_id: str) -> Dict[str, Any]:
        """
        Get aggregate stats for an activity across all users

        Args:
            activity_id: Activity ID

        Returns:
            Aggregate statistics
        """
        # Note: This requires listing all user impression files
        # For production, consider using a separate aggregate storage
        return {
            'activity_id': activity_id,
            'total_views': 0,
            'unique_viewers': 0,
            'message': 'Aggregate stats require scanning all users'
        }

    async def get_user_engagement_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Build a user's engagement profile for personalization

        Args:
            user_id: User ID

        Returns:
            Engagement profile with preferences
        """
        try:
            impressions_data = await self.get_user_impressions(user_id)
            impressions = impressions_data.get('impressions', {})

            # Analyze viewing patterns
            teams_viewed = {}
            players_viewed = {}
            goal_types_viewed = {}
            total_views = 0

            for activity_id, impression in impressions.items():
                view_count = impression.get('view_count', 0)
                total_views += view_count

                # Extract metadata from activity_id or stored metadata
                metadata = impression.get('metadata', {})

                # Track team preferences
                if 'team' in metadata:
                    team = metadata['team']
                    teams_viewed[team] = teams_viewed.get(team, 0) + view_count

                # Track player preferences
                if 'player_id' in metadata:
                    player_id = metadata['player_id']
                    players_viewed[player_id] = players_viewed.get(player_id, 0) + view_count

                # Track goal type preferences
                if 'goal_type' in metadata:
                    goal_type = metadata['goal_type']
                    goal_types_viewed[goal_type] = goal_types_viewed.get(goal_type, 0) + view_count

            # Sort by most viewed
            top_teams = sorted(teams_viewed.items(), key=lambda x: x[1], reverse=True)[:5]
            top_players = sorted(players_viewed.items(), key=lambda x: x[1], reverse=True)[:5]
            top_goal_types = sorted(goal_types_viewed.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                'user_id': user_id,
                'total_views': total_views,
                'unique_activities_viewed': len(impressions),
                'preferences': {
                    'teams': [{'team': t, 'views': v} for t, v in top_teams],
                    'players': [{'player_id': p, 'views': v} for p, v in top_players],
                    'goal_types': [{'type': gt, 'views': v} for gt, v in top_goal_types]
                }
            }

        except Exception as e:
            print(f"❌ Failed to build engagement profile: {str(e)}")
            return {
                'user_id': user_id,
                'total_views': 0,
                'preferences': {}
            }


# Singleton instance
analytics_tracker = None


def get_analytics_tracker() -> AnalyticsTracker:
    """Get or create analytics tracker singleton"""
    global analytics_tracker
    if analytics_tracker is None:
        from app.s3_storage import s3_storage
        analytics_tracker = AnalyticsTracker(s3_storage)
    return analytics_tracker
