"""
API routes for GetStream Activity Feeds
Platform-agnostic endpoints for querying feeds
"""
from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional, List
from app.stream_client import stream_client
from app.config import settings

router = APIRouter()


@router.get("/feeds/{feed_id}/activities")
async def get_feed_activities(
    feed_id: str = Path(..., description="Feed ID (e.g., 'COL', 'nhl')"),
    feed_group: str = Query(settings.DEFAULT_FEED_GROUP, description="Feed group name"),
    limit: int = Query(settings.DEFAULT_LIMIT, ge=1, le=settings.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    enrich: bool = Query(True, description="Enrich activities with referenced objects")
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
    Get recent activities from the central feed

    **Example:**
    - `GET /api/v1/activities/recent` - Get 20 most recent activities
    - `GET /api/v1/activities/recent?limit=50` - Get 50 most recent
    """
    return await get_feed_activities(
        feed_id=feed_id,
        feed_group=feed_group,
        limit=limit,
        offset=0,
        enrich=True
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
    Get activities with client-side filtering

    **Example:**
    - `GET /api/v1/activities/filter?tag=game-winner` - Game-winning activities
    - `GET /api/v1/activities/filter?filter_tag=COL` - Activities by team COL
    """
    try:
        # Fetch activities
        result = await stream_client.get_activities(
            feed_group=feed_group,
            feed_id=feed_id,
            limit=limit * 2,  # Fetch more to filter client-side
            enrich=True
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
    Get aggregated statistics for a feed

    **Example:**
    - `GET /api/v1/feeds/nhl/stats` - League-wide statistics
    - `GET /api/v1/feeds/COL/stats` - Team-specific statistics
    """
    try:
        result = await stream_client.get_activities(
            feed_group=feed_group,
            feed_id=feed_id,
            limit=limit,
            enrich=False
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
