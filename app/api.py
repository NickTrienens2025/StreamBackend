"""
API routes for GetStream Activity Feeds
Platform-agnostic endpoints for querying feeds
"""
from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional, List
from app.stream_client import stream_client
from app.s3_storage import s3_storage
from app.config import settings
import uuid

router = APIRouter()


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
