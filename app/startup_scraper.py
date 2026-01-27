"""
Startup Scraper Module
Runs scraper on service startup and tracks status in S3
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
from app.scraper_on_demand import check_for_new_goals
from app.s3_storage import S3Storage


async def run_startup_scraper(days_back: int = 3) -> Dict[str, Any]:
    """
    Run scraper on startup and track status

    Args:
        days_back: Number of days to check

    Returns:
        Scraper results and status
    """
    s3_storage = S3Storage()

    startup_status = {
        'started_at': datetime.utcnow().isoformat(),
        'status': 'running',
        'days_back': days_back,
        'error': None,
        'results': None
    }

    try:
        # Save initial status
        await s3_storage.write('scraper_startup_status.json', startup_status)

        print(f"\n🚀 Starting up - checking for new goals (last {days_back} days)...")

        # Run the scraper
        results = await check_for_new_goals(days_back=days_back, force_refresh=False)

        # Update status with results
        startup_status['status'] = 'completed'
        startup_status['completed_at'] = datetime.utcnow().isoformat()
        startup_status['results'] = results

        print(f"✅ Startup scraper completed: {results['new_goals']} new goals found\n")

    except Exception as e:
        print(f"❌ Startup scraper failed: {str(e)}\n")
        startup_status['status'] = 'failed'
        startup_status['completed_at'] = datetime.utcnow().isoformat()
        startup_status['error'] = str(e)

    finally:
        # Save final status
        try:
            await s3_storage.write('scraper_startup_status.json', startup_status)
            await s3_storage.close()
        except Exception as e:
            print(f"⚠️  Failed to save startup status: {str(e)}")

    return startup_status


async def get_startup_status() -> Dict[str, Any]:
    """
    Get the most recent startup scraper status

    Returns:
        Startup status data
    """
    s3_storage = S3Storage()

    try:
        status = await s3_storage.read('scraper_startup_status.json')
        if status:
            return status
    except Exception as e:
        print(f"⚠️  Could not load startup status: {str(e)}")
    finally:
        await s3_storage.close()

    return {
        'status': 'unknown',
        'message': 'No startup status found'
    }


async def save_startup_run_history(status: Dict[str, Any]) -> None:
    """
    Save startup run to history file

    Args:
        status: Startup status to archive
    """
    s3_storage = S3Storage()

    try:
        # Load existing history
        history = await s3_storage.read('scraper_startup_history.json') or {'runs': []}

        # Add this run
        history['runs'].insert(0, status)  # Most recent first

        # Keep only last 50 runs
        history['runs'] = history['runs'][:50]
        history['last_updated'] = datetime.utcnow().isoformat()

        # Save history
        await s3_storage.write('scraper_startup_history.json', history)

    except Exception as e:
        print(f"⚠️  Failed to save startup history: {str(e)}")
    finally:
        await s3_storage.close()
