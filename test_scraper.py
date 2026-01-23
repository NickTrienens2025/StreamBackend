"""
Test script for NHL scraper cron job
Tests scraping a specific date to verify functionality
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.nhl_scraper_cron import NHLScraperCron
from app.s3_storage import S3Storage
from app.config import settings
from stream.client import StreamClient as GetStreamClient
from datetime import date, timedelta


async def test_single_date(test_date: str = None):
    """
    Test scraping a single date

    Args:
        test_date: Date to test in YYYY-MM-DD format (defaults to yesterday)
    """
    if not test_date:
        # Default to yesterday
        test_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"\n🧪 Testing NHL Scraper with date: {test_date}")
    print("=" * 60)

    # Verify environment variables
    print("\n1️⃣ Checking environment variables...")
    if not settings.STREAM_API_KEY:
        print("❌ STREAM_API_KEY not set")
        return
    if not settings.STREAM_API_SECRET:
        print("❌ STREAM_API_SECRET not set")
        return
    print("✅ Environment variables OK")

    # Initialize clients
    print("\n2️⃣ Initializing clients...")
    try:
        stream_client = GetStreamClient(
            api_key=settings.STREAM_API_KEY,
            api_secret=settings.STREAM_API_SECRET,
            app_id=settings.STREAM_APP_ID
        )
        print("✅ GetStream client initialized")

        s3_storage = S3Storage()
        print("✅ S3 storage client initialized")

        scraper = NHLScraperCron(stream_client, s3_storage)
        print("✅ NHL scraper initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {str(e)}")
        return

    try:
        # Test S3 connectivity
        print("\n3️⃣ Testing S3 connectivity...")
        try:
            progress = await s3_storage.load_progress()
            print(f"✅ S3 connection OK - Found {len(progress.get('completed_dates', []))} completed dates")
        except Exception as e:
            print(f"⚠️  S3 load warning: {str(e)}")

        # Scrape test date
        print(f"\n4️⃣ Scraping NHL data for {test_date}...")
        summary = await scraper.scrape_date_range(test_date, test_date)

        # Display results
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        print(f"Date: {test_date}")
        print(f"Goals found: {summary.get('total_goals', 0)}")
        print(f"Successfully uploaded: {summary.get('total_uploaded', 0)}")
        print(f"Failed uploads: {summary.get('total_failed', 0)}")

        if summary.get('total_goals', 0) > 0:
            print("\n✅ Test PASSED - Goals were found and processed")
        else:
            print("\n⚠️  Test completed but no goals found (check if games were scheduled)")

    except Exception as e:
        print(f"\n❌ Test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        await scraper.close()
        await s3_storage.close()


async def test_progress_tracking():
    """Test S3 progress tracking functionality"""
    print("\n🧪 Testing S3 Progress Tracking")
    print("=" * 60)

    s3_storage = S3Storage()

    try:
        # Load progress
        print("\n1️⃣ Loading progress from S3...")
        progress = await s3_storage.load_progress()

        print(f"\nProgress data:")
        print(f"  Completed dates: {len(progress.get('completed_dates', []))}")
        print(f"  Failed dates: {len(progress.get('failed_dates', []))}")
        print(f"  Last updated: {progress.get('last_updated', 'Never')}")
        print(f"  Total goals: {progress.get('stats', {}).get('totalGoals', 0)}")

        if progress.get('completed_dates'):
            print(f"\n  Most recent completed: {sorted(progress['completed_dates'])[-1]}")
            print(f"  Oldest completed: {sorted(progress['completed_dates'])[0]}")

        print("\n✅ Progress tracking test PASSED")

    except Exception as e:
        print(f"\n❌ Progress tracking test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        await s3_storage.close()


async def test_api_connectivity():
    """Test NHL API connectivity"""
    print("\n🧪 Testing NHL API Connectivity")
    print("=" * 60)

    import httpx

    test_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test schedule API
            print(f"\n1️⃣ Testing schedule API for {test_date}...")
            url = f"https://api-web.nhle.com/v1/schedule/{test_date}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                game_count = 0
                if data.get('gameWeek'):
                    for day in data['gameWeek']:
                        if day.get('date') == test_date:
                            game_count = len(day.get('games', []))

                print(f"✅ Schedule API OK - Found {game_count} games")
            else:
                print(f"❌ Schedule API returned {response.status_code}")

        print("\n✅ NHL API connectivity test PASSED")

    except Exception as e:
        print(f"\n❌ NHL API connectivity test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 NHL SCRAPER - FULL TEST SUITE")
    print("=" * 60)

    await test_api_connectivity()
    await test_progress_tracking()

    # Test with yesterday's date (most likely to have completed games)
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    await test_single_date(yesterday)

    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test NHL scraper functionality')
    parser.add_argument('--date', type=str, help='Specific date to test (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--api', action='store_true', help='Test API connectivity only')
    parser.add_argument('--progress', action='store_true', help='Test progress tracking only')

    args = parser.parse_args()

    if args.all:
        asyncio.run(run_all_tests())
    elif args.api:
        asyncio.run(test_api_connectivity())
    elif args.progress:
        asyncio.run(test_progress_tracking())
    else:
        asyncio.run(test_single_date(args.date))
