"""
GetStream client wrapper
Provides methods for interacting with Activity Feeds
"""
from typing import List, Dict, Any, Optional
import re
from stream.client import StreamClient as GetStreamClient
from app.config import settings


def sanitize_user_id(user_id: str) -> str:
    """
    Sanitize user ID to be GetStream compatible

    GetStream user IDs cannot contain special characters like @, ., etc.

    Args:
        user_id: Raw user ID (may be email)

    Returns:
        Sanitized user ID safe for GetStream
    """
    # Replace @ with _at_
    sanitized = user_id.replace('@', '_at_')
    # Replace . with _
    sanitized = sanitized.replace('.', '_')
    # Remove any other non-alphanumeric characters except _ and -
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', sanitized)

    return sanitized


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
            user_id: User adding the reaction (will be sanitized)
            kind: Reaction type (e.g., 'like', 'heart', 'comment')
            activity_id: Activity ID (must be GetStream UUID, not foreign_id)
            data: Optional additional data

        Returns:
            Created reaction
        """
        try:
            # Sanitize user_id to remove special characters
            sanitized_user_id = sanitize_user_id(user_id)

            print(f"🎯 Adding reaction: kind={kind}, activity={activity_id}")
            print(f"   User: {user_id} → {sanitized_user_id}")

            # GetStream SDK: reactions.add(kind, activity_id, user_id, data={}, target_feeds=[])
            response = self.client.reactions.add(
                kind=kind,
                activity_id=activity_id,
                user_id=sanitized_user_id,
                data=data or {}
            )

            print(f"✅ Reaction added successfully: {response.get('id')}")
            return response

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Failed to add reaction: {error_msg}")
            print(f"   Activity ID: {activity_id}")
            print(f"   User ID: {user_id} (sanitized: {sanitize_user_id(user_id)})")
            print(f"   Kind: {kind}")

            # Provide helpful error message
            if "must be a valid UUID" in error_msg:
                raise Exception(
                    f"GetStream error: activity_id must be the GetStream UUID (id field), "
                    f"not the foreign_id. Got: {activity_id}"
                )
            elif "invalid characters" in error_msg:
                raise Exception(
                    f"GetStream error: user_id contains invalid characters. "
                    f"Original: {user_id}, Sanitized: {sanitize_user_id(user_id)}"
                )
            else:
                raise Exception(f"GetStream reaction error: {error_msg}")

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
            user_id: User ID (will be sanitized)
            activity_id: Activity ID
            kind: Reaction kind

        Returns:
            Reaction if exists, None otherwise
        """
        sanitized_user_id = sanitize_user_id(user_id)
        reactions = await self.get_reactions(activity_id, kind=kind, user_id=sanitized_user_id)
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
            user_id: User ID to get reactions for (will be sanitized)
            limit: Number of activities
            offset: Pagination offset

        Returns:
            Activities with reaction data
        """
        # Sanitize user_id
        sanitized_user_id = sanitize_user_id(user_id)

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
            'user_id': sanitized_user_id  # Important for own_reactions
        }

        response = feed.get(**options)

        return {
            'results': response.get('results', []),
            'next': response.get('next'),
            'duration': response.get('duration')
        }


# Singleton client instance
stream_client = StreamClient()
