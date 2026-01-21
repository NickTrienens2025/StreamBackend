"""
GetStream client wrapper
Provides methods for interacting with Activity Feeds
"""
from typing import List, Dict, Any, Optional
from stream.client import StreamClient as GetStreamClient
from app.config import settings


class StreamClient:
    """Wrapper for GetStream Activity Feeds client"""

    def __init__(self):
        """Initialize GetStream client"""
        self.client = GetStreamClient(
            api_key=settings.STREAM_API_KEY,
            api_secret=settings.STREAM_API_SECRET,
            app_id=settings.STREAM_APP_ID
        )

    def get_feed(self, feed_group: str, feed_id: str):
        """Get a feed instance"""
        return self.client.feed(feed_group, feed_id)

    async def get_activities(
        self,
        feed_group: str,
        feed_id: str,
        limit: int = 25,
        offset: int = 0,
        enrich: bool = True,
        ranking: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get activities from a feed

        Args:
            feed_group: Feed group name (e.g., 'goals')
            feed_id: Feed ID (e.g., 'COL', 'nhl')
            limit: Number of activities to retrieve
            offset: Pagination offset
            enrich: Whether to enrich activities with referenced objects
            ranking: Optional ranking method

        Returns:
            Dict with activities and metadata
        """
        feed = self.get_feed(feed_group, feed_id)

        options = {
            'limit': min(limit, settings.MAX_LIMIT),
            'offset': offset,
            'enrich': enrich
        }

        if ranking:
            options['ranking'] = ranking

        response = feed.get(**options)

        return {
            'results': response.get('results', []),
            'next': response.get('next'),
            'duration': response.get('duration')
        }

    async def query_activities(
        self,
        feed_ids: List[str],
        limit: int = 25,
        enrich: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query activities across multiple feeds

        Args:
            feed_ids: List of feed IDs (e.g., ['goals:COL', 'goals:TOR'])
            limit: Number of activities to retrieve
            enrich: Whether to enrich activities
            filters: Optional filters for activities

        Returns:
            Dict with activities and metadata
        """
        # Note: This is a placeholder for multi-feed queries
        # Actual implementation depends on GetStream SDK capabilities
        # For now, we'll query the first feed
        if not feed_ids:
            return {'results': [], 'next': None}

        # Parse first feed_id (format: 'group:id')
        parts = feed_ids[0].split(':')
        if len(parts) == 2:
            feed_group, feed_id = parts
            return await self.get_activities(feed_group, feed_id, limit, enrich=enrich)

        return {'results': [], 'next': None}

    async def add_activity(
        self,
        feed_group: str,
        feed_id: str,
        activity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add an activity to a feed

        Args:
            feed_group: Feed group name
            feed_id: Feed ID
            activity: Activity data

        Returns:
            Created activity
        """
        feed = self.get_feed(feed_group, feed_id)
        response = feed.add_activity(activity)
        return response

    async def get_collections(
        self,
        collection_name: str,
        ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get objects from a collection

        Args:
            collection_name: Collection name (e.g., 'goals')
            ids: List of object IDs

        Returns:
            List of collection objects
        """
        response = self.client.collections.select(collection_name, ids)
        return response.get('response', {}).get('data', [])

    def generate_feed_token(
        self,
        feed_group: str,
        feed_id: str,
        resource: str = "activities",
        action: str = "*"
    ) -> str:
        """
        Generate a client-side feed token

        Args:
            feed_group: Feed group name
            feed_id: Feed ID
            resource: Resource to grant access to
            action: Action to allow

        Returns:
            JWT token for client-side access
        """
        feed = self.get_feed(feed_group, feed_id)
        return feed.token

    def follow_feed(
        self,
        feed_group: str,
        feed_id: str,
        target_feed_group: str,
        target_feed_id: str
    ):
        """
        Follow a target feed

        Args:
            feed_group: Source feed group
            feed_id: Source feed ID
            target_feed_group: Target feed group
            target_feed_id: Target feed ID
        """
        feed = self.get_feed(feed_group, feed_id)
        feed.follow(target_feed_group, target_feed_id)

    def create_user_token(self, user_id: str) -> str:
        """
        Create a user token for client-side authentication

        Args:
            user_id: User ID

        Returns:
            JWT user token
        """
        return self.client.create_user_token(user_id)


# Singleton client instance
stream_client = StreamClient()
