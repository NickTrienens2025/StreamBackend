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

    async def add_reaction(
        self,
        user_id: str,
        kind: str,
        activity_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a reaction to an activity

        Args:
            user_id: User adding the reaction
            kind: Reaction type (e.g., 'like', 'heart', 'comment')
            activity_id: Activity ID
            data: Optional additional data

        Returns:
            Created reaction
        """
        reaction_data = {
            'kind': kind,
            'activity_id': activity_id,
            'user_id': user_id
        }

        if data:
            reaction_data['data'] = data

        response = self.client.reactions.add(kind, activity_id, user_id, data=data or {})
        return response

    async def remove_reaction(self, reaction_id: str) -> bool:
        """
        Remove a reaction

        Args:
            reaction_id: Reaction ID to remove

        Returns:
            Success status
        """
        try:
            self.client.reactions.delete(reaction_id)
            return True
        except Exception:
            return False

    async def get_reactions(
        self,
        activity_id: str,
        kind: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get reactions for an activity

        Args:
            activity_id: Activity ID
            kind: Optional filter by reaction kind
            user_id: Optional filter by user

        Returns:
            List of reactions
        """
        params = {
            'activity_id': activity_id,
            'limit': 100
        }

        if kind:
            params['kind'] = kind

        response = self.client.reactions.filter(activity_id=activity_id, kind=kind, limit=100)
        reactions = response.get('results', [])

        if user_id:
            reactions = [r for r in reactions if r.get('user_id') == user_id]

        return reactions

    async def get_user_reaction(
        self,
        user_id: str,
        activity_id: str,
        kind: str = 'like'
    ) -> Optional[Dict[str, Any]]:
        """
        Get a user's specific reaction on an activity

        Args:
            user_id: User ID
            activity_id: Activity ID
            kind: Reaction kind

        Returns:
            Reaction if exists, None otherwise
        """
        reactions = await self.get_reactions(activity_id, kind=kind, user_id=user_id)
        return reactions[0] if reactions else None

    async def get_activities_with_reactions(
        self,
        feed_group: str,
        feed_id: str,
        user_id: str,
        limit: int = 25,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get activities enriched with user's reaction state

        Args:
            feed_group: Feed group name
            feed_id: Feed ID
            user_id: User ID to get reactions for
            limit: Number of activities
            offset: Pagination offset

        Returns:
            Activities with reaction data
        """
        # Get activities with enrichment
        feed = self.get_feed(feed_group, feed_id)

        options = {
            'limit': min(limit, settings.MAX_LIMIT),
            'offset': offset,
            'enrich': True,
            'reactions': {
                'recent': True,
                'own': True,
                'counts': True
            },
            'user_id': user_id  # Important for own_reactions
        }

        response = feed.get(**options)

        return {
            'results': response.get('results', []),
            'next': response.get('next'),
            'duration': response.get('duration')
        }


# Singleton client instance
stream_client = StreamClient()
