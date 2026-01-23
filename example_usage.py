"""
NHL Scraper - Example Usage
Examples of how to use the scraper programmatically
"""

import asyncio
from datetime import date, timedelta
from app.nhl_scraper_cron import NHLScraperCron
from app.s3_storage import S3Storage
from app.config import settings
from stream.client import StreamClient as GetStreamClient


async def example_1_scrape_to_today():
    """
    Example 1: Scrape from last completed date to today
    This is what the cron job does automatically
    """
    print("\n📖 Example 1: Scrape to Today")
    print("=" * 60)

    # Initialize
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )
    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    try:
        # Scrape from last completed date to today
        summary = await scraper.scrape_to_today()

        print(f"\n✅ Completed!")
        print(f"Dates processed: {summary['dates_processed']}")
        print(f"Total goals: {summary['total_goals']}")
        print(f"Uploaded: {summary['total_uploaded']}")

    finally:
        await scraper.close()
        await s3_storage.close()


async def example_2_scrape_specific_date():
    """
    Example 2: Scrape a specific date
    Useful for backfilling or testing
    """
    print("\n📖 Example 2: Scrape Specific Date")
    print("=" * 60)

    # Initialize
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )
    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    try:
        # Scrape a specific date (e.g., yesterday)
        target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        summary = await scraper.scrape_date_range(target_date, target_date)

        print(f"\n✅ Scraped {target_date}")
        print(f"Goals found: {summary['total_goals']}")

    finally:
        await scraper.close()
        await s3_storage.close()


async def example_3_scrape_date_range():
    """
    Example 3: Scrape a date range
    Useful for historical backfilling
    """
    print("\n📖 Example 3: Scrape Date Range")
    print("=" * 60)

    # Initialize
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )
    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    try:
        # Scrape last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        summary = await scraper.scrape_date_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        print(f"\n✅ Scraped {start_date} to {end_date}")
        print(f"Dates processed: {summary['dates_processed']}")
        print(f"Total goals: {summary['total_goals']}")

    finally:
        await scraper.close()
        await s3_storage.close()


async def example_4_check_progress():
    """
    Example 4: Check scraping progress
    View what dates have been completed
    """
    print("\n📖 Example 4: Check Progress")
    print("=" * 60)

    s3_storage = S3Storage()

    try:
        # Load progress
        progress = await s3_storage.load_progress()

        completed = progress.get('completed_dates', [])
        failed = progress.get('failed_dates', [])
        total_goals = progress.get('stats', {}).get('totalGoals', 0)

        print(f"\nCompleted dates: {len(completed)}")
        print(f"Failed dates: {len(failed)}")
        print(f"Total goals scraped: {total_goals}")

        if completed:
            completed.sort()
            print(f"\nDate range: {completed[0]} to {completed[-1]}")
            print(f"Last update: {progress.get('last_updated', 'Unknown')}")

        if failed:
            print(f"\n⚠️  Failed dates: {', '.join(failed)}")

    finally:
        await s3_storage.close()


async def example_5_scrape_single_game():
    """
    Example 5: Scrape data for a single date and inspect the goals
    """
    print("\n📖 Example 5: Scrape and Inspect Goals")
    print("=" * 60)

    # Initialize
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )
    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    try:
        # Scrape yesterday
        target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        print(f"\n🔍 Scraping goals for {target_date}...")
        goals_data = await scraper.scrape_nhl_goals(target_date)

        print(f"\n✅ Found {len(goals_data)} goals")

        # Inspect first few goals
        for i, goal in enumerate(goals_data[:3]):
            activity = goal['activity']
            print(f"\n📊 Goal {i+1}:")
            print(f"  Player: {activity['scoring_player_name']}")
            print(f"  Team: {activity['scoring_team']} vs {activity['opponent']}")
            print(f"  Score: {activity['home_score']}-{activity['away_score']}")
            print(f"  Period: {activity['period']}")
            print(f"  Game Winner: {activity['is_game_winner']}")
            print(f"  Importance Score: {activity['score']}")

    finally:
        await scraper.close()
        await s3_storage.close()


async def example_6_backfill_month():
    """
    Example 6: Backfill an entire month
    Useful for historical data
    """
    print("\n📖 Example 6: Backfill Entire Month")
    print("=" * 60)

    # Initialize
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )
    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    try:
        # Backfill January 2026
        start_date = '2026-01-01'
        end_date = '2026-01-31'

        print(f"\n🔄 Backfilling {start_date} to {end_date}...")
        print("This may take 20-30 minutes...")

        summary = await scraper.scrape_date_range(start_date, end_date)

        print(f"\n✅ Backfill complete!")
        print(f"Dates processed: {summary['dates_processed']}")
        print(f"Total goals: {summary['total_goals']}")
        print(f"Uploaded: {summary['total_uploaded']}")
        print(f"Failed: {summary['total_failed']}")

    finally:
        await scraper.close()
        await s3_storage.close()


async def example_7_retry_failed_dates():
    """
    Example 7: Retry dates that previously failed
    """
    print("\n📖 Example 7: Retry Failed Dates")
    print("=" * 60)

    # Initialize
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )
    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    try:
        # Load progress to find failed dates
        progress = await s3_storage.load_progress()
        failed_dates = progress.get('failed_dates', [])

        if not failed_dates:
            print("✅ No failed dates to retry!")
            return

        print(f"\n⚠️  Found {len(failed_dates)} failed dates")
        print(f"Dates: {', '.join(failed_dates)}")

        # Clear failed dates and retry
        progress['failed_dates'] = []
        await s3_storage.save_progress(progress)

        # Retry each failed date
        for failed_date in failed_dates:
            print(f"\n🔄 Retrying {failed_date}...")
            try:
                summary = await scraper.scrape_date_range(failed_date, failed_date)
                print(f"✅ {failed_date} - Success: {summary['total_goals']} goals")
            except Exception as e:
                print(f"❌ {failed_date} - Failed again: {str(e)}")

    finally:
        await scraper.close()
        await s3_storage.close()


async def example_8_get_recent_goals():
    """
    Example 8: Get recently scraped goals from GetStream
    """
    print("\n📖 Example 8: Query Recent Goals from GetStream")
    print("=" * 60)

    # Initialize
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )

    try:
        # Get recent goals from NHL feed
        nhl_feed = stream_client.feed('goals', 'nhl')
        response = nhl_feed.get(limit=10, enrich=True)

        activities = response.get('results', [])

        print(f"\n✅ Found {len(activities)} recent goals")

        for activity in activities[:5]:
            print(f"\n🏒 {activity.get('scoring_player_name')}")
            print(f"   Team: {activity.get('scoring_team')} vs {activity.get('opponent')}")
            print(f"   Score: {activity.get('home_score')}-{activity.get('away_score')}")
            print(f"   Game Winner: {activity.get('is_game_winner')}")

    finally:
        pass


# Run examples
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("NHL SCRAPER - USAGE EXAMPLES")
    print("=" * 60)

    # Uncomment the example you want to run:

    # asyncio.run(example_1_scrape_to_today())
    # asyncio.run(example_2_scrape_specific_date())
    # asyncio.run(example_3_scrape_date_range())
    asyncio.run(example_4_check_progress())
    # asyncio.run(example_5_scrape_single_game())
    # asyncio.run(example_6_backfill_month())
    # asyncio.run(example_7_retry_failed_dates())
    # asyncio.run(example_8_get_recent_goals())
