"""
On-Demand NHL Goals Scraper
Checks for new goals but only marks days complete when all games are finished
"""

import asyncio
import httpx
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from app.nhl_scraper_cron import NHLScraperCron
from app.s3_storage import S3Storage
from app.config import settings
from stream.client import StreamClient as GetStreamClient


NHL_API_BASE = 'https://api-web.nhle.com/v1'


async def are_all_games_finished(date_str: str) -> Dict[str, Any]:
    """
    Check if all games on a specific date are finished

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Dict with game status information
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{NHL_API_BASE}/schedule/{date_str}")

            if response.status_code != 200:
                raise Exception(f"Schedule API returned {response.status_code}")

            data = response.json()

            if not data.get('gameWeek') or len(data['gameWeek']) == 0:
                # No games scheduled = day is "complete"
                return {
                    'all_finished': True,
                    'total_games': 0,
                    'finished_games': 0,
                    'live_games': 0,
                    'future_games': 0,
                    'games': []
                }

            day_data = None
            for day in data['gameWeek']:
                if day.get('date') == date_str:
                    day_data = day
                    break

            if not day_data or not day_data.get('games'):
                return {
                    'all_finished': True,
                    'total_games': 0,
                    'finished_games': 0,
                    'live_games': 0,
                    'future_games': 0,
                    'games': []
                }

            games = day_data['games']

            # Check if all games have a final state
            # Game states: FUT (future), LIVE, FINAL, OFF (official final)
            finished_states = {'FINAL', 'OFF'}
            all_finished = all(game.get('gameState') in finished_states for game in games)

            live_games = [g for g in games if g.get('gameState') == 'LIVE']
            future_games = [g for g in games if g.get('gameState') == 'FUT']
            finished_games = [g for g in games if g.get('gameState') in finished_states]

            return {
                'all_finished': all_finished,
                'total_games': len(games),
                'finished_games': len(finished_games),
                'live_games': len(live_games),
                'future_games': len(future_games),
                'games': [
                    {
                        'id': game.get('id'),
                        'state': game.get('gameState'),
                        'away': game.get('awayTeam', {}).get('abbrev'),
                        'home': game.get('homeTeam', {}).get('abbrev')
                    }
                    for game in games
                ]
            }

    except Exception as e:
        return {
            'all_finished': False,
            'error': str(e)
        }


def get_recent_dates(days_back: int = 3) -> List[str]:
    """
    Get dates to check (last N days including today)

    Args:
        days_back: Number of days to look back

    Returns:
        List of date strings in YYYY-MM-DD format
    """
    dates = []
    today = date.today()

    for i in range(days_back + 1):
        check_date = today - timedelta(days=i)
        dates.append(check_date.strftime('%Y-%m-%d'))

    return list(reversed(dates))  # oldest first


async def check_for_new_goals(days_back: int = 3, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Check for new goals and upload them
    Only marks days as complete when all games are finished

    Args:
        days_back: Number of days to look back (default 3)
        force_refresh: If True, re-scrape even completed days

    Returns:
        Summary of results
    """
    print('\n🏒 Checking for new NHL goals...')
    print('=' * 60)

    # Initialize clients
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )

    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    try:
        # Load progress
        progress = await s3_storage.load_progress()
        completed_dates = set(progress.get('completed_dates', []))
        in_progress_dates = set(progress.get('in_progress_dates', []))

        # Get dates to check
        dates_to_check = get_recent_dates(days_back)

        results = {
            'checked': 0,
            'new_goals': 0,
            'uploaded': 0,
            'days_completed': 0,
            'days_in_progress': 0,
            'details': []
        }

        for date_str in dates_to_check:
            try:
                # Skip if already completed (unless force refresh)
                if date_str in completed_dates and not force_refresh:
                    print(f'\n📅 {date_str}: Already complete, skipping')
                    continue

                print(f'\n📅 {date_str}: Checking...')
                results['checked'] += 1

                # Check game status
                game_status = await are_all_games_finished(date_str)

                if 'error' in game_status:
                    print(f"  ⚠️  Could not verify game status: {game_status['error']}")
                    results['details'].append({
                        'date': date_str,
                        'status': 'error',
                        'message': game_status['error']
                    })
                    continue

                print(f"  🎮 Games: {game_status['total_games']} total, "
                      f"{game_status['finished_games']} finished, "
                      f"{game_status['live_games']} live, "
                      f"{game_status['future_games']} upcoming")

                # Scrape goals for this date
                goals_data = await scraper.scrape_nhl_goals(date_str)

                if goals_data:
                    print(f"  ⚽ Found {len(goals_data)} goals")
                    results['new_goals'] += len(goals_data)

                    # Upload to GetStream
                    print(f"  📤 Uploading to GetStream...")
                    upload_result = await scraper.upload_goals_with_collections(goals_data)
                    results['uploaded'] += upload_result['uploaded']

                    print(f"  ✅ Uploaded: {upload_result['uploaded']}, Failed: {upload_result['failed']}")
                else:
                    print(f"  ℹ️  No goals found")

                # Update progress based on game status
                if game_status['all_finished']:
                    # All games finished - mark as complete
                    if date_str not in completed_dates:
                        completed_dates.add(date_str)
                        progress['completed_dates'] = list(completed_dates)
                        results['days_completed'] += 1
                        print(f"  ✅ Day marked as COMPLETE (all games finished)")

                    # Remove from in-progress if it was there
                    if date_str in in_progress_dates:
                        in_progress_dates.discard(date_str)
                        progress['in_progress_dates'] = list(in_progress_dates)

                    results['details'].append({
                        'date': date_str,
                        'status': 'complete',
                        'goals': len(goals_data) if goals_data else 0,
                        'games': game_status
                    })
                else:
                    # Games still in progress - mark as in-progress
                    if date_str not in in_progress_dates:
                        in_progress_dates.add(date_str)
                        progress['in_progress_dates'] = list(in_progress_dates)
                        results['days_in_progress'] += 1

                    print(f"  ⏳ Day marked as IN PROGRESS "
                          f"({game_status['live_games']} live, {game_status['future_games']} upcoming)")

                    results['details'].append({
                        'date': date_str,
                        'status': 'in_progress',
                        'goals': len(goals_data) if goals_data else 0,
                        'games': game_status
                    })

                # Update stats
                if 'stats' not in progress:
                    progress['stats'] = {'totalGoals': 0}

                progress['stats']['totalGoals'] = progress['stats'].get('totalGoals', 0) + (len(goals_data) if goals_data else 0)
                progress['last_updated'] = datetime.utcnow().isoformat()

                # Save progress
                await s3_storage.save_progress(progress)

                # Small delay between dates
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                results['details'].append({
                    'date': date_str,
                    'status': 'error',
                    'error': str(e)
                })

        print('\n' + '=' * 60)
        print('📊 SUMMARY')
        print('=' * 60)
        print(f"Dates checked:        {results['checked']}")
        print(f"New goals found:      {results['new_goals']}")
        print(f"Goals uploaded:       {results['uploaded']}")
        print(f"Days completed:       {results['days_completed']}")
        print(f"Days in progress:     {results['days_in_progress']}")
        print(f"Total completed days: {len(completed_dates)}")

        return results

    finally:
        await scraper.close()
        await s3_storage.close()


# CLI entry point
if __name__ == '__main__':
    import sys

    args = sys.argv[1:]
    force_refresh = '--force' in args or '--refresh' in args

    days_back = 3
    for arg in args:
        if arg.startswith('--days='):
            days_back = int(arg.split('=')[1])

    asyncio.run(check_for_new_goals(days_back=days_back, force_refresh=force_refresh))
