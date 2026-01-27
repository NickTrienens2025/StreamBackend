"""
API routes for GetStream Activity Feeds
Platform-agnostic endpoints for querying feeds
"""
from fastapi import APIRouter, Query, HTTPException, Path, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.stream_client import stream_client
from app.s3_storage import s3_storage
from app.config import settings
import uuid

router = APIRouter()


# Request models
class ImpressionRequest(BaseModel):
    user_id: Optional[str] = None
    userId: Optional[str] = None  # Support both snake_case and camelCase
    activity_id: Optional[str] = None
    activityId: Optional[str] = None  # Support both formats
    metadata: Optional[Dict[str, Any]] = None

    def get_user_id(self) -> str:
        """Get user_id from either format"""
        return self.user_id or self.userId or "unknown"

    def get_activity_id(self) -> str:
        """Get activity_id from either format"""
        return self.activity_id or self.activityId or "unknown"


class ReactionRequest(BaseModel):
    user_id: Optional[str] = None
    userId: Optional[str] = None  # Support both formats
    activity_id: Optional[str] = None
    activityId: Optional[str] = None  # Support both formats
    kind: str = "like"
    data: Optional[Dict[str, Any]] = None

    def get_user_id(self) -> str:
        """Get user_id from either format"""
        return self.user_id or self.userId or "unknown"

    def get_activity_id(self) -> str:
        """Get activity_id from either format"""
        return self.activity_id or self.activityId or "unknown"


@router.get("/auth/default-user")
async def get_default_user(alias: Optional[str] = Query(None, description="User alias (e.g., user1)")):
    """
    Get or create a persistent default user
    """
    try:
        filename = f"user_{alias}.json" if alias else "default_user.json"
        user_data = await s3_storage.read(filename)
        
        if not user_data:
            prefix = f"web-{alias}-" if alias else "web-guest-"
            user_id = f"{prefix}{uuid.uuid4().hex[:8]}"
            user_data = {"user_id": user_id}
            await s3_storage.write(filename, user_data)
        
        user_id = user_data["user_id"]
        token = stream_client.create_user_token(user_id)
        
        # Ensure user follows the default feed
        try:
            stream_client.follow_feed("user", user_id, "goals", "COL")
        except:
            pass # Ignore if already following

        return {
            "success": True,
            "user_id": user_id,
            "token": token,
            "api_key": settings.STREAM_API_KEY,
            "app_id": settings.STREAM_APP_ID
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get default user: {str(e)}")


@router.get("/feeds/{feed_id}/activities")
async def get_feed_activities(
    feed_id: str = Path(..., description="Feed ID (e.g., 'COL', 'nhl')"),
    feed_group: str = Query(settings.DEFAULT_FEED_GROUP, description="Feed group name"),
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    enrich: bool = True  # Always enrich - full data with collections
):
    """
    Get activities from a specific feed

    **Example:**
    - `GET /api/v1/feeds/nhl/activities` - Get all activities from central feed
    - `GET /api/v1/feeds/COL/activities` - Get activities for team COL
    - `GET /api/v1/feeds/nhl/activities?limit=10` - Get 10 most recent
    """
    try:
        result = await stream_client.get_activities(
            feed_group=feed_group,
            feed_id=feed_id,
            limit=limit,
            offset=offset,
            enrich=enrich
        )

        return {
            "success": True,
            "feed": f"{feed_group}:{feed_id}",
            "count": len(result.get('results', [])),
            "data": result.get('results', []),
            "next": result.get('next'),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": result.get('next') is not None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activities: {str(e)}")


@router.get("/activities/recent")
async def get_recent_activities(
    feed_id: str = Query(settings.CENTRAL_FEED_ID, description="Feed ID to query"),
    feed_group: str = Query(settings.DEFAULT_FEED_GROUP),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get recent activities from the central feed (always enriched with full data)

    **Example:**
    - `GET /api/v1/activities/recent` - Get 20 most recent activities
    - `GET /api/v1/activities/recent?limit=50` - Get 50 most recent
    """
    return await get_feed_activities(
        feed_id=feed_id,
        feed_group=feed_group,
        limit=limit,
        offset=0
    )


@router.get("/activities/filter")
async def filter_activities(
    feed_id: str = Query(settings.CENTRAL_FEED_ID),
    feed_group: str = Query(settings.DEFAULT_FEED_GROUP),
    tag: Optional[str] = Query(None, description="Filter by interest tag (e.g., 'game-winner')"),
    filter_tag: Optional[str] = Query(None, description="Filter by filter tag (e.g., 'COL')"),
    limit: int = Query(50, ge=1, le=settings.MAX_LIMIT)
):
    """
    Get activities with client-side filtering (always enriched with full data)

    **Example:**
    - `GET /api/v1/activities/filter?tag=game-winner` - Game-winning activities
    - `GET /api/v1/activities/filter?filter_tag=COL` - Activities by team COL
    """
    try:
        # Fetch activities with full enrichment
        result = await stream_client.get_activities(
            feed_group=feed_group,
            feed_id=feed_id,
            limit=limit * 2,  # Fetch more to filter client-side
            enrich=True  # Always enrich
        )

        activities = result.get('results', [])

        # Apply client-side filters
        if tag:
            activities = [
                a for a in activities
                if tag in a.get('interest_tags', [])
            ]

        if filter_tag:
            activities = [
                a for a in activities
                if filter_tag in a.get('filter_tags', [])
            ]

        # Limit results
        activities = activities[:limit]

        return {
            "success": True,
            "filters": {
                "interest_tag": tag,
                "filter_tag": filter_tag
            },
            "count": len(activities),
            "data": activities
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to filter activities: {str(e)}")


@router.get("/feeds/{feed_id}/stats")
async def get_feed_stats(
    feed_id: str = Path(...),
    feed_group: str = Query(settings.DEFAULT_FEED_GROUP),
    limit: int = Query(1000, ge=1, le=settings.MAX_LIMIT)
):
    """
    Get aggregated statistics for a feed (enriched for complete data)

    **Example:**
    - `GET /api/v1/feeds/nhl/stats` - League-wide statistics
    - `GET /api/v1/feeds/COL/stats` - Team-specific statistics
    """
    try:
        result = await stream_client.get_activities(
            feed_group=feed_group,
            feed_id=feed_id,
            limit=limit,
            enrich=True  # Always enrich for complete stats
        )

        activities = result.get('results', [])

        # Calculate statistics
        stats = {
            "total_activities": len(activities),
            "by_type": {},
            "by_tag": {},
            "by_filter_tag": {}
        }

        for activity in activities:
            # Count by type
            activity_type = activity.get('verb', 'unknown')
            stats['by_type'][activity_type] = stats['by_type'].get(activity_type, 0) + 1

            # Count by interest tags
            for tag in activity.get('interest_tags', []):
                stats['by_tag'][tag] = stats['by_tag'].get(tag, 0) + 1

            # Count by filter tags
            for tag in activity.get('filter_tags', []):
                stats['by_filter_tag'][tag] = stats['by_filter_tag'].get(tag, 0) + 1

        return {
            "success": True,
            "feed": f"{feed_group}:{feed_id}",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate stats: {str(e)}")


@router.get("/token/{feed_id}")
async def get_feed_token(
    feed_id: str = Path(..., description="Feed ID"),
    feed_group: str = Query(settings.DEFAULT_FEED_GROUP)
):
    """
    Generate a client-side feed token for frontend apps

    **Example:**
    - `GET /api/v1/token/user123` - Get token for user's feed
    """
    try:
        token = stream_client.generate_feed_token(
            feed_group=feed_group,
            feed_id=feed_id
        )

        return {
            "success": True,
            "feed": f"{feed_group}:{feed_id}",
            "token": token,
            "api_key": settings.STREAM_API_KEY
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")


@router.post("/feeds/{feed_id}/follow")
async def follow_feed(
    feed_id: str = Path(..., description="Source Feed ID"),
    feed_group: str = Query("user", description="Source Feed Group"),
    target_feed_group: str = Query(..., description="Target Feed Group"),
    target_feed_id: str = Query(..., description="Target Feed ID")
):
    """
    Follow a target feed

    **Example:**
    - `POST /api/v1/feeds/user123/follow?target_feed_group=goals&target_feed_id=COL`
    """
    try:
        stream_client.follow_feed(
            feed_group=feed_group,
            feed_id=feed_id,
            target_feed_group=target_feed_group,
            target_feed_id=target_feed_id
        )

        return {
            "success": True,
            "message": f"{feed_group}:{feed_id} is now following {target_feed_group}:{target_feed_id}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to follow feed: {str(e)}")


@router.get("/collections/{collection_name}")
async def get_collection_objects(
    collection_name: str = Path(..., description="Collection name"),
    ids: List[str] = Query(..., description="Object IDs to fetch")
):
    """
    Get objects from a GetStream collection

    **Example:**
    - `GET /api/v1/collections/goals?ids=goal123&ids=goal456`
    """
    try:
        objects = await stream_client.get_collections(
            collection_name=collection_name,
            ids=ids
        )

        return {
            "success": True,
            "collection": collection_name,
            "count": len(objects),
            "data": objects
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch collection: {str(e)}")


# S3 Storage Endpoints

@router.get("/storage/progress")
async def get_scrape_progress():
    """
    Get scrape progress from S3 storage

    **Example:**
    - `GET /api/v1/storage/progress` - Get current scrape progress
    """
    if not settings.S3_ENABLED:
        raise HTTPException(status_code=503, detail="S3 storage is disabled")

    try:
        progress = await s3_storage.load_progress()
        return {
            "success": True,
            "data": progress
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch progress: {str(e)}")


@router.get("/storage/summaries")
async def list_scrape_summaries():
    """
    List all scrape summaries from S3 storage

    **Example:**
    - `GET /api/v1/storage/summaries` - List all summary files
    """
    if not settings.S3_ENABLED:
        raise HTTPException(status_code=503, detail="S3 storage is disabled")

    try:
        summaries = await s3_storage.list_summaries()
        return {
            "success": True,
            "count": len(summaries),
            "data": summaries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list summaries: {str(e)}")


@router.get("/storage/{key}")
async def get_storage_data(
    key: str = Path(..., description="Storage key (filename)")
):
    """
    Get data from S3 storage by key

    **Example:**
    - `GET /api/v1/storage/scrape_progress.json` - Get progress file
    - `GET /api/v1/storage/scrape_summary_2026-01-20.json` - Get specific summary
    """
    if not settings.S3_ENABLED:
        raise HTTPException(status_code=503, detail="S3 storage is disabled")

    try:
        data = await s3_storage.read(key)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Key not found: {key}")

        return {
            "success": True,
            "key": key,
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")


@router.get("/activities/filters/options")
async def get_filter_options():
    """
    Get available filter options and metadata for frontend clients
    """
    teams = [
        'ANA', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI', 'COL', 'DAL', 'DET',
        'EDM', 'FLA', 'LAK', 'MIN', 'MTL', 'NJD', 'NSH', 'NYI', 'NYR', 'OTT',
        'PHI', 'PIT', 'SEA', 'SJS', 'STL', 'TBL', 'TOR', 'VAN', 'VGK', 'WPG', 'WSH'
    ]

    return {
        "success": True,
        "groups": [
            {
                "title": "Teams",
                "apiKey": "team",
                "options": [{"label": team, "id": team} for team in teams]
            },
            {
                "title": "Goal Types",
                "apiKey": "interest_tag",
                "options": [
                    {"label": "Game Winner", "id": "game-winner"},
                    {"label": "Overtime", "id": "overtime"},
                    {"label": "Shootout", "id": "shootout"},
                    {"label": "Empty Net", "id": "empty-net"},
                    {"label": "Penalty Shot", "id": "penalty-shot"},
                    {"label": "Power Play", "id": "powerplay"},
                    {"label": "Short Handed", "id": "shorthanded"}
                ]
            },
            {
                "title": "Clutch Situations",
                "apiKey": "interest_tag",
                "options": [
                    {"label": "Tying Goal", "id": "tying-goal"},
                    {"label": "Go-Ahead Goal", "id": "go-ahead-goal"},
                    {"label": "Comeback Goal", "id": "comeback"},
                    {"label": "Late Period (<2 min)", "id": "late-period"},
                    {"label": "Buzzer Beater (<30 sec)", "id": "buzzer-beater"},
                    {"label": "Close Game (1-goal diff)", "id": "close-game"},
                    {"label": "First Goal of Game", "id": "first-goal"}
                ]
            },
            {
                "title": "Shot Types",
                "apiKey": "interest_tag",
                "options": [
                    {"label": "Wrist Shot", "id": "shot:wrist"},
                    {"label": "Snap Shot", "id": "shot:snap"},
                    {"label": "Slap Shot", "id": "shot:slap"},
                    {"label": "Backhand", "id": "shot:backhand"},
                    {"label": "Tip-In", "id": "shot:tip-in"},
                    {"label": "Wrap-Around", "id": "shot:wrap-around"},
                    {"label": "Deflected", "id": "shot:deflected"}
                ]
            }
        ],
        "sort_options": [
            {"label": "Latest First", "id": "time", "default": True},
            {"label": "Most Important", "id": "score", "default": False}
        ]
    }


# Scraper Endpoints

@router.post("/scraper/check-for-new-goals")
async def check_for_new_goals_endpoint(
    days_back: int = Query(3, ge=1, le=7, description="Number of days to look back"),
    force_refresh: bool = Query(False, description="Force re-scrape of completed days")
):
    """
    Check for new NHL goals and upload them to GetStream
    Only marks days as complete when all games are finished

    This endpoint should be called when the app starts the feed experience
    to ensure the latest data is available.

    **Example:**
    - `POST /api/v1/scraper/check-for-new-goals` - Check last 3 days
    - `POST /api/v1/scraper/check-for-new-goals?days_back=5` - Check last 5 days
    - `POST /api/v1/scraper/check-for-new-goals?force_refresh=true` - Force refresh all days
    """
    try:
        from app.scraper_on_demand import check_for_new_goals

        results = await check_for_new_goals(days_back=days_back, force_refresh=force_refresh)

        return {
            "success": True,
            "message": "Goal check completed",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check for new goals: {str(e)}")


@router.get("/scraper/game-status/{date}")
async def get_game_status(
    date: str = Path(..., description="Date in YYYY-MM-DD format")
):
    """
    Check if all games on a specific date are finished

    **Example:**
    - `GET /api/v1/scraper/game-status/2026-01-27` - Check game status for date
    """
    try:
        from app.scraper_on_demand import are_all_games_finished

        status = await are_all_games_finished(date)

        return {
            "success": True,
            "date": date,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check game status: {str(e)}")


@router.get("/scraper/startup-status")
async def get_startup_scraper_status():
    """
    Get the status of the most recent startup scraper run

    This endpoint returns information about the scraper that runs
    automatically when the service starts up.

    **Example:**
    - `GET /api/v1/scraper/startup-status` - Get startup scraper status
    """
    try:
        from app.startup_scraper import get_startup_status

        status = await get_startup_status()

        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get startup status: {str(e)}")


@router.get("/scraper/startup-history")
async def get_startup_scraper_history():
    """
    Get the history of startup scraper runs

    Returns the last 50 startup scraper runs with their results.

    **Example:**
    - `GET /api/v1/scraper/startup-history` - Get startup run history
    """
    if not settings.S3_ENABLED:
        raise HTTPException(status_code=503, detail="S3 storage is disabled")

    try:
        history = await s3_storage.read('scraper_startup_history.json')

        if not history:
            return {
                "success": True,
                "runs": [],
                "message": "No startup history found"
            }

        return {
            "success": True,
            "runs": history.get('runs', []),
            "last_updated": history.get('last_updated')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get startup history: {str(e)}")


# Analytics Endpoints

@router.post("/analytics/debug")
async def debug_analytics_request(request: Dict[str, Any] = Body(...)):
    """
    Debug endpoint to see raw request data from iOS app

    **Example:**
    - Send any JSON and it will echo back what was received
    """
    print(f"📋 Debug request received: {request}")
    return {
        "success": True,
        "received": request,
        "message": "Debug data received successfully"
    }


@router.post("/analytics/impression")
async def track_impression(request: ImpressionRequest):
    """
    Track an impression (view) of an activity

    Called by the iOS app when an activity scrolls into view (60% visible).

    Accepts both snake_case (user_id, activity_id) and camelCase (userId, activityId).

    **Example:**
    ```json
    {
        "user_id": "user123",
        "activity_id": "goal:2025020826_123",
        "metadata": {
            "team": "CGY",
            "player_id": "8477018",
            "goal_type": "go-ahead-goal"
        }
    }
    ```
    """
    try:
        from app.analytics import get_analytics_tracker

        user_id = request.get_user_id()
        activity_id = request.get_activity_id()

        # Debug logging
        print(f"📊 Impression: user={user_id}, activity={activity_id}")

        tracker = get_analytics_tracker()
        success = await tracker.track_impression(
            user_id=user_id,
            activity_id=activity_id,
            metadata=request.metadata
        )

        return {
            "success": success,
            "message": "Impression tracked" if success else "Failed to track impression"
        }
    except Exception as e:
        print(f"❌ Impression tracking error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to track impression: {str(e)}")


@router.post("/analytics/reaction")
async def track_reaction_legacy(request: ReactionRequest):
    """
    Track a reaction (legacy endpoint for iOS app compatibility)

    This is an alias for /reactions/add to support existing iOS app code.
    The iOS app calls this endpoint when a user likes/hearts an activity.

    **Example:**
    ```json
    {
        "user_id": "ntrienens@nhl.com",
        "activity_id": "b227dc00-fb1f-11f0-8080-8001429e601f",
        "kind": "like"
    }
    ```
    """
    try:
        reaction = await stream_client.add_reaction(
            user_id=request.get_user_id(),
            kind=request.kind,
            activity_id=request.get_activity_id(),
            data=request.data
        )

        return {
            "success": True,
            "reaction": reaction,
            "message": "Reaction tracked"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track reaction: {str(e)}")


@router.get("/analytics/user/{user_id}/profile")
async def get_user_engagement_profile(user_id: str = Path(...)):
    """
    Get a user's engagement profile for personalization

    Returns viewing preferences based on impression history.

    **Example:**
    - `GET /api/v1/analytics/user/user123/profile`
    """
    try:
        from app.analytics import get_analytics_tracker

        tracker = get_analytics_tracker()
        profile = await tracker.get_user_engagement_profile(user_id)

        return {
            "success": True,
            "profile": profile
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get engagement profile: {str(e)}")


@router.get("/analytics/user/{user_id}/impressions")
async def get_user_impressions(user_id: str = Path(...)):
    """
    Get all impressions for a user

    **Example:**
    - `GET /api/v1/analytics/user/user123/impressions`
    """
    try:
        from app.analytics import get_analytics_tracker

        tracker = get_analytics_tracker()
        impressions = await tracker.get_user_impressions(user_id)

        return {
            "success": True,
            "impressions": impressions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get impressions: {str(e)}")


# Reactions Endpoints

@router.post("/reactions/add")
async def add_reaction(request: ReactionRequest):
    """
    Add a reaction (like, heart, etc.) to an activity

    **Example:**
    ```json
    {
        "user_id": "user123",
        "activity_id": "goal:2025020826_123",
        "kind": "like"
    }
    ```
    """
    try:
        reaction = await stream_client.add_reaction(
            user_id=request.get_user_id(),
            kind=request.kind,
            activity_id=request.get_activity_id(),
            data=request.data
        )

        return {
            "success": True,
            "reaction": reaction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add reaction: {str(e)}")


@router.delete("/reactions/{reaction_id}")
async def remove_reaction(reaction_id: str = Path(...)):
    """
    Remove a reaction

    **Example:**
    - `DELETE /api/v1/reactions/abc123`
    """
    try:
        success = await stream_client.remove_reaction(reaction_id)

        return {
            "success": success,
            "message": "Reaction removed" if success else "Failed to remove reaction"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove reaction: {str(e)}")


@router.get("/reactions/activity/{activity_id}")
async def get_activity_reactions(
    activity_id: str = Path(...),
    kind: Optional[str] = Query(None, description="Filter by reaction kind (like, heart, etc.)")
):
    """
    Get all reactions for an activity

    **Example:**
    - `GET /api/v1/reactions/activity/goal:2025020826_123`
    - `GET /api/v1/reactions/activity/goal:2025020826_123?kind=like`
    """
    try:
        reactions = await stream_client.get_reactions(activity_id, kind=kind)

        return {
            "success": True,
            "activity_id": activity_id,
            "count": len(reactions),
            "reactions": reactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reactions: {str(e)}")


@router.get("/reactions/user/{user_id}/activity/{activity_id}")
async def get_user_reaction_for_activity(
    user_id: str = Path(...),
    activity_id: str = Path(...),
    kind: str = Query("like", description="Reaction kind")
):
    """
    Check if a user has reacted to an activity

    Returns the user's reaction if it exists.

    **Example:**
    - `GET /api/v1/reactions/user/user123/activity/goal:2025020826_123?kind=like`
    """
    try:
        reaction = await stream_client.get_user_reaction(user_id, activity_id, kind)

        return {
            "success": True,
            "user_id": user_id,
            "activity_id": activity_id,
            "has_reacted": reaction is not None,
            "reaction": reaction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check user reaction: {str(e)}")


# Personalized Feed Endpoints

@router.get("/feeds/{feed_id}/personalized")
async def get_personalized_feed(
    feed_id: str = Path(..., description="Feed ID (e.g., 'nhl')"),
    user_id: str = Query(..., description="User ID for personalization"),
    feed_group: str = Query(settings.DEFAULT_FEED_GROUP),
    limit: int = Query(50, ge=1, le=settings.MAX_LIMIT)
):
    """
    Get a personalized feed for a user with reactions

    This endpoint returns activities enriched with:
    - User's own reactions (own_reactions)
    - Reaction counts (reaction_counts)
    - Whether the user has liked each activity

    **Example:**
    - `GET /api/v1/feeds/nhl/personalized?user_id=user123&limit=50`
    """
    try:
        # Get activities with reaction enrichment
        result = await stream_client.get_activities_with_reactions(
            feed_group=feed_group,
            feed_id=feed_id,
            user_id=user_id,
            limit=limit
        )

        # Get user's engagement profile for additional personalization
        from app.analytics import get_analytics_tracker
        tracker = get_analytics_tracker()
        profile = await tracker.get_user_engagement_profile(user_id)

        return {
            "success": True,
            "feed": f"{feed_group}:{feed_id}",
            "user_id": user_id,
            "count": len(result.get('results', [])),
            "data": result.get('results', []),
            "next": result.get('next'),
            "personalization": {
                "top_teams": profile.get('preferences', {}).get('teams', [])[:3],
                "total_views": profile.get('total_views', 0)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch personalized feed: {str(e)}")
