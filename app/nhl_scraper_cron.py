"""
NHL Goals Scraper V2 - Python Version for Cron Jobs
Features:
- S3-based progress tracking
- Scrapes from last processed date to today
- Game-winning goal detection
- Full player enrichment from roster data
- Brightcove video data integration
- Collections & Activities upload to GetStream
- Advanced goal importance ranking
- Interest tags and filter tags
"""

import asyncio
import httpx
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Set, Tuple
import json
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.s3_storage import S3Storage
from app.config import settings
from stream.client import StreamClient as GetStreamClient


NHL_API_BASE = 'https://api-web.nhle.com/v1'


class NHLScraperCron:
    """NHL Goals Scraper with S3 progress tracking"""

    def __init__(self, stream_client: GetStreamClient, s3_storage: S3Storage):
        self.stream_client = stream_client
        self.s3_storage = s3_storage
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Clean up resources"""
        await self.http_client.aclose()

    async def scrape_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Scrape NHL goals for a date range

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (inclusive)

        Returns:
            Summary with stats
        """
        print(f"\n🏒 NHL Goals Scraper - Date Range: {start_date} to {end_date}")
        print("=" * 60)

        # Load existing progress
        progress = await self.s3_storage.load_progress()
        completed_dates = set(progress.get('completed_dates', []))
        failed_dates = set(progress.get('failed_dates', []))

        # Generate date list
        current = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        dates_to_scrape = []

        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            if date_str not in completed_dates and date_str not in failed_dates:
                dates_to_scrape.append(date_str)
            current += timedelta(days=1)

        if not dates_to_scrape:
            print("✅ All dates in range already processed")
            return {
                'dates_processed': 0,
                'total_goals': 0,
                'message': 'All dates already completed'
            }

        print(f"📅 Dates to process: {len(dates_to_scrape)}")
        print(f"📅 Already completed: {len(completed_dates)}")

        total_goals = 0
        total_uploaded = 0
        total_failed = 0
        dates_processed = 0

        for date_str in dates_to_scrape:
            try:
                print(f"\n📆 Processing date: {date_str}")
                print("-" * 40)

                # Scrape goals for this date
                goals_data = await self.scrape_nhl_goals(date_str)

                if goals_data:
                    # Upload to GetStream
                    upload_stats = await self.upload_goals_with_collections(goals_data)

                    total_goals += len(goals_data)
                    total_uploaded += upload_stats['uploaded']
                    total_failed += upload_stats['failed']

                    print(f"✅ Date {date_str}: {len(goals_data)} goals, "
                          f"{upload_stats['uploaded']} uploaded, "
                          f"{upload_stats['failed']} failed")
                else:
                    print(f"ℹ️  No goals found for {date_str}")

                # Mark as completed
                completed_dates.add(date_str)
                dates_processed += 1

                # Save progress after each date
                progress['completed_dates'] = list(completed_dates)
                progress['stats']['totalGoals'] = progress.get('stats', {}).get('totalGoals', 0) + len(goals_data)
                await self.s3_storage.save_progress(progress)

                # Rate limiting between dates
                await asyncio.sleep(1)

            except Exception as e:
                print(f"❌ Error processing {date_str}: {str(e)}")
                failed_dates.add(date_str)
                progress['failed_dates'] = list(failed_dates)
                await self.s3_storage.save_progress(progress)

        # Final summary
        summary = {
            'date_range': f"{start_date} to {end_date}",
            'dates_processed': dates_processed,
            'total_goals': total_goals,
            'total_uploaded': total_uploaded,
            'total_failed': total_failed,
            'completed': list(completed_dates),
            'failed': list(failed_dates)
        }

        # Save summary to S3
        timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        await self.s3_storage.save_summary(summary, timestamp)

        print("\n" + "=" * 60)
        print("📊 SCRAPE SUMMARY")
        print("=" * 60)
        print(f"Dates processed: {dates_processed}")
        print(f"Total goals found: {total_goals}")
        print(f"Successfully uploaded: {total_uploaded}")
        print(f"Failed uploads: {total_failed}")

        return summary

    async def scrape_to_today(self) -> Dict[str, Any]:
        """
        Scrape from last completed date to today

        Returns:
            Summary with stats
        """
        # Load progress to find last completed date
        progress = await self.s3_storage.load_progress()
        completed_dates = progress.get('completed_dates', [])

        if completed_dates:
            # Find most recent completed date
            completed_dates.sort()
            last_date_str = completed_dates[-1]
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
            start_date = last_date + timedelta(days=1)
        else:
            # Default to yesterday if no progress
            start_date = date.today() - timedelta(days=1)

        end_date = date.today()

        return await self.scrape_date_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

    async def scrape_nhl_goals(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Scrape NHL goals for a specific date

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            List of goal data with activities and collection objects
        """
        try:
            # Get schedule for the date
            schedule_url = f"{NHL_API_BASE}/schedule/{date_str}"
            response = await self.http_client.get(schedule_url)

            if response.status_code != 200:
                raise Exception(f"Schedule API returned {response.status_code}")

            schedule_data = response.json()

            if not schedule_data.get('gameWeek') or len(schedule_data['gameWeek']) == 0:
                return []

            all_goal_data = []

            # Process each day
            for day in schedule_data['gameWeek']:
                if day.get('date') != date_str:
                    continue

                games = day.get('games', [])
                if not games:
                    continue

                print(f"  🎮 Found {len(games)} games")

                # Process each game
                for game in games:
                    try:
                        game_goals = await self.process_game(game)
                        all_goal_data.extend(game_goals)

                        # Rate limiting
                        await asyncio.sleep(0.1)

                    except Exception as e:
                        print(f"  ⚠️  Error processing game {game.get('id')}: {str(e)}")

            return all_goal_data

        except Exception as e:
            raise Exception(f"Failed to scrape date {date_str}: {str(e)}")

    async def process_game(self, game: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a complete game and calculate game-winning goals

        Args:
            game: Game data from schedule API

        Returns:
            List of goal data
        """
        game_url = f"{NHL_API_BASE}/gamecenter/{game['id']}/play-by-play"
        response = await self.http_client.get(game_url)

        if response.status_code != 200:
            print(f"  ⚠️  Game {game['id']} returned {response.status_code}")
            return []

        game_data = response.json()

        if not game_data.get('plays'):
            return []

        # Build roster lookup for player names
        roster_lookup = self.build_roster_lookup(game_data)

        # Extract all goals from the game
        goals = []
        for play in game_data['plays']:
            if play.get('typeDescKey') == 'goal':
                goals.append({'play': play, 'game': game, 'gameData': game_data})

        if not goals:
            return []

        # Fetch brightcove data once for entire game
        game_brightcove_map = {}
        needs_brightcove = any(
            not g['play'].get('highlightClip') and not g['play'].get('discreteClip')
            for g in goals
        )

        if needs_brightcove:
            print(f"  🎥 Fetching brightcove data for game {game['id']} ({len(goals)} goals)...")
            game_brightcove_map = await self.fetch_game_brightcove_data(game['id'])
            found_count = sum(
                1 for v in game_brightcove_map.values()
                if v.get('highlightClip') or v.get('discreteClip')
            )
            print(f"  ✅ Found brightcove data for {found_count}/{len(goals)} goals")

        # Determine game-winning goal and piling-on goals
        game_winner_id, piling_on_ids = self.calculate_game_winner(goals, game)

        # Convert goals to activities with Collections
        results = []
        for goal_info in goals:
            result = self.convert_goal_to_collection_and_activity(
                goal_info['play'],
                goal_info['game'],
                goal_info['gameData'],
                game_winner_id,
                piling_on_ids,
                roster_lookup,
                game_brightcove_map
            )
            if result:
                results.append(result)

        return results

    def build_roster_lookup(self, game_data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """
        Build a roster lookup map from game data

        Args:
            game_data: Game data from NHL API

        Returns:
            Map of playerId -> player data
        """
        roster_map = {}

        roster_spots = game_data.get('rosterSpots', [])
        if not isinstance(roster_spots, list):
            return roster_map

        for player in roster_spots:
            player_id = player.get('playerId')
            if player_id:
                roster_map[player_id] = {
                    'playerId': player_id,
                    'firstName': player.get('firstName'),
                    'lastName': player.get('lastName'),
                    'sweaterNumber': player.get('sweaterNumber'),
                    'position': player.get('positionCode'),
                    'headshot': player.get('headshot'),
                    'teamId': player.get('teamId')
                }

        return roster_map

    async def fetch_game_brightcove_data(self, game_id: str) -> Dict[int, Dict[str, Any]]:
        """
        Fetch all brightcove IDs for a game from mobile API

        Args:
            game_id: Game ID

        Returns:
            Map of eventId -> brightcove data
        """
        try:
            mobile_url = f"{NHL_API_BASE}/gamecenter/{game_id}/landing"
            response = await self.http_client.get(mobile_url)

            if response.status_code != 200:
                return {}

            data = response.json()
            brightcove_map = {}

            # Extract brightcove data from all goals in the game
            summary = data.get('summary', {})
            scoring = summary.get('scoring', [])

            for period in scoring:
                goals = period.get('goals', [])
                for goal in goals:
                    event_id = goal.get('eventId')
                    if event_id:
                        brightcove_map[event_id] = {
                            'highlightClip': goal.get('highlightClip'),
                            'discreteClip': goal.get('discreteClip')
                        }

            return brightcove_map

        except Exception as e:
            print(f"  ⚠️  Mobile API failed for game {game_id}: {str(e)}")
            return {}

    def calculate_game_winner(
        self,
        goals: List[Dict[str, Any]],
        game: Dict[str, Any]
    ) -> Tuple[Optional[str], Set[str]]:
        """
        Calculate which goal was the game-winner and identify piling-on goals

        Args:
            goals: List of goal data
            game: Game data

        Returns:
            Tuple of (game_winner_id, piling_on_ids)
        """
        if not goals:
            return None, set()

        # Get final score from last goal
        last_goal = goals[-1]
        details = last_goal['play'].get('details', {})
        final_home_score = details.get('homeScore', 0)
        final_away_score = details.get('awayScore', 0)

        # Determine winner
        home_team = game.get('homeTeam', {})
        away_team = game.get('awayTeam', {})
        winning_team = home_team.get('abbrev') if final_home_score > final_away_score else away_team.get('abbrev')

        game_winner_id = None
        piling_on_ids = set()
        last_lead_change_goal = None

        # Walk through all goals chronologically
        for goal_info in goals:
            play = goal_info['play']
            details = play.get('details', {})

            scoring_team = (
                home_team.get('abbrev')
                if details.get('eventOwnerTeamId') == home_team.get('id')
                else away_team.get('abbrev')
            )

            home_score = details.get('homeScore', 0)
            away_score = details.get('awayScore', 0)

            # Calculate previous score (before this goal)
            prev_home_score = home_score - 1 if scoring_team == home_team.get('abbrev') else home_score
            prev_away_score = away_score - 1 if scoring_team == away_team.get('abbrev') else away_score

            goal_id = f"{game['id']}_{play.get('eventId')}"

            # Check if this goal gave the scoring team the lead
            if scoring_team == home_team.get('abbrev'):
                took_lead = prev_home_score <= prev_away_score and home_score > away_score
            else:
                took_lead = prev_away_score <= prev_home_score and away_score > home_score

            # If the winning team scored this goal
            if scoring_team == winning_team:
                if took_lead:
                    # This goal gave them the lead - track as potential game-winner
                    last_lead_change_goal = goal_id
                elif last_lead_change_goal is not None:
                    # Already ahead and scoring more = piling on
                    if scoring_team == home_team.get('abbrev'):
                        was_already_ahead = prev_home_score > prev_away_score
                    else:
                        was_already_ahead = prev_away_score > prev_home_score

                    if was_already_ahead:
                        piling_on_ids.add(goal_id)

        # The last goal that gave the winning team the lead is the game-winner
        game_winner_id = last_lead_change_goal

        return game_winner_id, piling_on_ids

    def convert_goal_to_collection_and_activity(
        self,
        play: Dict[str, Any],
        game: Dict[str, Any],
        game_data: Dict[str, Any],
        game_winner_id: Optional[str],
        piling_on_ids: Set[str],
        roster_lookup: Dict[int, Dict[str, Any]],
        game_brightcove_map: Dict[int, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert goal to Collection object and Activity with all queryable fields

        Returns:
            Dict with goalObject, activity, and goalId
        """
        try:
            details = play.get('details', {})

            # Check for brightcove IDs
            brightcove_data = {
                'highlightClip': play.get('highlightClip'),
                'discreteClip': play.get('discreteClip')
            }

            # If no brightcove data in play-by-play, look up from game brightcove map
            event_id = play.get('eventId')
            if not brightcove_data['highlightClip'] and not brightcove_data['discreteClip']:
                cached_data = game_brightcove_map.get(event_id, {})
                if cached_data:
                    brightcove_data = cached_data

            # Look up player data from roster
            scoring_player = roster_lookup.get(details.get('scoringPlayerId'), {})
            assist_players = []

            assist1_id = details.get('assist1PlayerId')
            if assist1_id:
                assist1 = roster_lookup.get(assist1_id)
                if assist1:
                    assist_players.append(assist1)

            assist2_id = details.get('assist2PlayerId')
            if assist2_id:
                assist2 = roster_lookup.get(assist2_id)
                if assist2:
                    assist_players.append(assist2)

            goalie_player = roster_lookup.get(details.get('goalieInNetId'))

            # Determine scoring team and opponent
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})

            scoring_team = (
                home_team.get('abbrev')
                if details.get('eventOwnerTeamId') == home_team.get('id')
                else away_team.get('abbrev')
            )

            opponent = (
                away_team.get('abbrev')
                if scoring_team == home_team.get('abbrev')
                else home_team.get('abbrev')
            )

            goal_id = f"{game['id']}_{event_id}"
            is_game_winner = goal_id == game_winner_id
            is_piling_on = goal_id in piling_on_ids

            # Get scores after this goal
            home_score = details.get('homeScore', 0)
            away_score = details.get('awayScore', 0)

            # Calculate scores before this goal
            is_home_goal = scoring_team == home_team.get('abbrev')
            prev_home_score = home_score - 1 if is_home_goal else home_score
            prev_away_score = away_score - 1 if is_home_goal else away_score

            # Helper function to get localized text
            def get_text(obj, default=''):
                if isinstance(obj, dict):
                    return obj.get('default', default)
                return obj or default

            # Collection object - Complete goal data for enrichment
            goal_object = {
                # Identifiers
                'goal_id': goal_id,
                'game_id': game['id'],
                'event_id': event_id,

                # Brightcove Video IDs
                'highlight_clip': brightcove_data.get('highlightClip'),
                'highlight_clip_default': (
                    brightcove_data['highlightClip'].get('default')
                    if isinstance(brightcove_data.get('highlightClip'), dict)
                    else brightcove_data.get('highlightClip')
                ),
                'highlight_clip_fr': (
                    brightcove_data['highlightClip'].get('fr')
                    if isinstance(brightcove_data.get('highlightClip'), dict)
                    else None
                ),
                'discrete_clip': brightcove_data.get('discreteClip'),
                'discrete_clip_default': (
                    brightcove_data['discreteClip'].get('default')
                    if isinstance(brightcove_data.get('discreteClip'), dict)
                    else brightcove_data.get('discreteClip')
                ),
                'discrete_clip_fr': (
                    brightcove_data['discreteClip'].get('fr')
                    if isinstance(brightcove_data.get('discreteClip'), dict)
                    else None
                ),

                # Timing
                'period': play.get('periodDescriptor', {}).get('number', 0),
                'period_type': play.get('periodDescriptor', {}).get('periodType', 'REG'),
                'time_in_period': play.get('timeInPeriod', '00:00'),
                'time_remaining': play.get('timeRemaining', '00:00'),
                'game_date': game.get('gameDate'),
                'game_time': game.get('startTimeUTC', game.get('gameDate')),

                # Scoring player (detailed)
                'scoring_player': {
                    'id': str(scoring_player.get('playerId', 'unknown')),
                    'first_name': get_text(scoring_player.get('firstName')),
                    'last_name': get_text(scoring_player.get('lastName')),
                    'full_name': (
                        f"{get_text(scoring_player.get('firstName'))} "
                        f"{get_text(scoring_player.get('lastName'))}"
                    ).strip() or 'Unknown',
                    'sweater_number': scoring_player.get('sweaterNumber'),
                    'position': scoring_player.get('position'),
                    'headshot': scoring_player.get('headshot'),
                    'team_abbrev': scoring_team,
                    'team_name': (
                        get_text(home_team.get('name'))
                        if details.get('eventOwnerTeamId') == home_team.get('id')
                        else get_text(away_team.get('name'))
                    )
                },

                # Teams
                'goal_for_team': scoring_team,
                'goal_against_team': opponent,

                'scoring_team': {
                    'abbrev': scoring_team,
                    'name': (
                        get_text(home_team.get('name'))
                        if scoring_team == home_team.get('abbrev')
                        else get_text(away_team.get('name'))
                    ),
                    'is_home': scoring_team == home_team.get('abbrev')
                },

                'opponent': {
                    'abbrev': opponent,
                    'name': (
                        get_text(home_team.get('name'))
                        if opponent == home_team.get('abbrev')
                        else get_text(away_team.get('name'))
                    ),
                    'is_home': opponent == home_team.get('abbrev')
                },

                # Shot details
                'shot_type': details.get('shotType', 'unknown'),
                'shot_details': {
                    'x_coord': details.get('xCoord'),
                    'y_coord': details.get('yCoord'),
                    'zone_code': details.get('zoneCode')
                },

                # Goal classification
                'goal_type': details.get('goalModifier', 'even-strength'),
                'strength': details.get('strength', 'even'),
                'empty_net': details.get('goalModifier') == 'empty-net',
                'penalty_shot': details.get('goalModifier') == 'penalty-shot',

                # Game situation
                'is_game_winner': is_game_winner,
                'is_overtime': play.get('periodDescriptor', {}).get('number', 0) > 3,
                'is_shootout': play.get('periodDescriptor', {}).get('periodType') == 'SO',

                # Assists
                'assists': [
                    {
                        'id': str(assist.get('playerId', 'unknown')),
                        'first_name': get_text(assist.get('firstName')),
                        'last_name': get_text(assist.get('lastName')),
                        'full_name': (
                            f"{get_text(assist.get('firstName'))} "
                            f"{get_text(assist.get('lastName'))}"
                        ).strip(),
                        'sweater_number': assist.get('sweaterNumber'),
                        'position': assist.get('position'),
                        'headshot': assist.get('headshot'),
                        'team_abbrev': scoring_team,
                        'type': 'primary' if idx == 0 else 'secondary'
                    }
                    for idx, assist in enumerate(assist_players)
                ],

                # Goalie
                'goalie': (
                    {
                        'id': str(goalie_player.get('playerId')) if goalie_player else None,
                        'first_name': get_text(goalie_player.get('firstName')) if goalie_player else '',
                        'last_name': get_text(goalie_player.get('lastName')) if goalie_player else '',
                        'full_name': (
                            f"{get_text(goalie_player.get('firstName'))} "
                            f"{get_text(goalie_player.get('lastName'))}"
                        ).strip() if goalie_player else '',
                        'team_abbrev': opponent,
                        'headshot': goalie_player.get('headshot') if goalie_player else None
                    } if goalie_player else None
                ),

                # Score context
                'home_team': home_team.get('abbrev'),
                'away_team': away_team.get('abbrev'),
                'home_score': home_score,
                'away_score': away_score,
                'score_differential': abs(home_score - away_score),

                # Venue
                'venue': get_text(game.get('venue'), 'Unknown'),

                # Description
                'description': (
                    f"{get_text(scoring_player.get('firstName'))} "
                    f"{get_text(scoring_player.get('lastName'))} "
                    f"({scoring_team}) - {details.get('shotType', 'shot')}"
                ),
                'situation_code': details.get('situationCode', '')
            }

            # Calculate goal importance
            period_desc = play.get('periodDescriptor', {})
            importance_context = {
                'isGameWinner': is_game_winner,
                'period': period_desc.get('number', 0),
                'periodType': period_desc.get('periodType'),
                'goalModifier': details.get('goalModifier'),
                'strength': details.get('strength'),
                'timeInPeriod': play.get('timeInPeriod'),
                'timeRemaining': play.get('timeRemaining'),
                'homeScore': home_score,
                'awayScore': away_score,
                'prevHomeScore': prev_home_score,
                'prevAwayScore': prev_away_score,
                'scoringTeam': scoring_team,
                'homeTeam': home_team.get('abbrev')
            }

            importance_score = self.calculate_goal_importance(importance_context)

            # Generate tags
            interest_tags_context = {
                'homeScore': home_score,
                'awayScore': away_score,
                'prevHomeScore': prev_home_score,
                'prevAwayScore': prev_away_score,
                'isHomeGoal': is_home_goal,
                'timeRemaining': play.get('timeRemaining')
            }

            interest_tags = self.generate_interest_tags(
                scoring_team,
                opponent,
                scoring_player,
                details,
                play,
                is_game_winner,
                is_piling_on,
                interest_tags_context
            )

            filter_tags = self.generate_filter_tags(scoring_team, scoring_player)

            # Activity - Root-level queryable fields + Collection reference
            activity = {
                # Required Activity Feeds fields
                'actor': f"team:{scoring_team}",
                'verb': 'score',
                'object': f"goal:{goal_id}",
                'foreign_id': f"goal:{goal_id}",
                'time': game.get('startTimeUTC', game.get('gameDate')),

                # Queryable fields - Player dimension
                'scoring_player_id': str(scoring_player.get('playerId', 'unknown')),
                'scoring_player_name': (
                    f"{get_text(scoring_player.get('firstName'))} "
                    f"{get_text(scoring_player.get('lastName'))}"
                ).strip() or 'Unknown',
                'scoring_player_headshot': scoring_player.get('headshot'),
                'scoring_player_position': scoring_player.get('position'),
                'scoring_player_sweater': scoring_player.get('sweaterNumber'),

                # Assist dimensions
                'primary_assist_id': (
                    str(assist_players[0].get('playerId'))
                    if assist_players else None
                ),
                'primary_assist_name': (
                    f"{get_text(assist_players[0].get('firstName'))} "
                    f"{get_text(assist_players[0].get('lastName'))}"
                ).strip() if assist_players else None,
                'secondary_assist_id': (
                    str(assist_players[1].get('playerId'))
                    if len(assist_players) > 1 else None
                ),
                'secondary_assist_name': (
                    f"{get_text(assist_players[1].get('firstName'))} "
                    f"{get_text(assist_players[1].get('lastName'))}"
                ).strip() if len(assist_players) > 1 else None,
                'assists_count': len(assist_players),

                # Team dimensions
                'scoring_team': scoring_team,
                'opponent': opponent,
                'goal_for_team': scoring_team,
                'goal_against_team': opponent,
                'home_team': home_team.get('abbrev'),
                'away_team': away_team.get('abbrev'),
                'is_home_goal': is_home_goal,

                # Brightcove Video IDs
                'highlight_clip_default': (
                    brightcove_data['highlightClip'].get('default')
                    if isinstance(brightcove_data.get('highlightClip'), dict)
                    else brightcove_data.get('highlightClip')
                ),
                'highlight_clip_fr': (
                    brightcove_data['highlightClip'].get('fr')
                    if isinstance(brightcove_data.get('highlightClip'), dict)
                    else None
                ),
                'discrete_clip_default': (
                    brightcove_data['discreteClip'].get('default')
                    if isinstance(brightcove_data.get('discreteClip'), dict)
                    else brightcove_data.get('discreteClip')
                ),
                'discrete_clip_fr': (
                    brightcove_data['discreteClip'].get('fr')
                    if isinstance(brightcove_data.get('discreteClip'), dict)
                    else None
                ),

                # Shot type dimension
                'shot_type': details.get('shotType', 'unknown'),
                'shot_x_coord': details.get('xCoord'),
                'shot_y_coord': details.get('yCoord'),
                'shot_zone': details.get('zoneCode'),

                # Goalie dimension
                'goalie_id': str(details.get('goalieInNetId')) if details.get('goalieInNetId') else None,
                'goalie_team': opponent,

                # Goal type dimensions
                'goal_type': details.get('goalModifier', 'even-strength'),
                'strength': details.get('strength', 'even'),

                # Special classifications
                'is_game_winner': is_game_winner,
                'is_overtime': period_desc.get('number', 0) > 3,
                'is_shootout': period_desc.get('periodType') == 'SO',
                'is_empty_net': details.get('goalModifier') == 'empty-net',
                'is_penalty_shot': details.get('goalModifier') == 'penalty-shot',
                'is_power_play': details.get('strength') == 'powerplay',
                'is_short_handed': details.get('strength') == 'shorthanded',

                # Comeback classifications
                'is_tying_goal': prev_home_score != prev_away_score and home_score == away_score,
                'is_go_ahead_goal': (
                    (is_home_goal and prev_home_score <= prev_away_score and home_score > away_score) or
                    (not is_home_goal and prev_away_score <= prev_home_score and away_score > home_score)
                ),

                # Game context
                'game_id': str(game['id']),
                'period': period_desc.get('number', 0),
                'period_type': period_desc.get('periodType', 'REG'),

                # Timing context
                'time_in_period': play.get('timeInPeriod', '00:00'),
                'time_remaining': play.get('timeRemaining', '00:00'),

                # Score context
                'home_score': home_score,
                'away_score': away_score,

                # Ranking score
                'score': importance_score,

                # Interest tags
                'interest_tags': interest_tags,

                # Filter tags
                'filter_tags': filter_tags
            }

            return {
                'goalObject': goal_object,
                'activity': activity,
                'goalId': goal_id
            }

        except Exception as e:
            print(f"  ⚠️  Error converting goal: {str(e)}")
            return None

    def calculate_goal_importance(self, context: Dict[str, Any]) -> int:
        """
        Calculate goal importance for ranking
        Higher score = more important goal
        """
        score = 1  # Base score

        is_game_winner = context.get('isGameWinner', False)
        period = context.get('period', 0)
        period_type = context.get('periodType')
        goal_modifier = context.get('goalModifier')
        strength = context.get('strength')
        time_remaining = context.get('timeRemaining', '00:00')
        home_score = context.get('homeScore', 0)
        away_score = context.get('awayScore', 0)
        prev_home_score = context.get('prevHomeScore', 0)
        prev_away_score = context.get('prevAwayScore', 0)
        scoring_team = context.get('scoringTeam')
        home_team = context.get('homeTeam')

        # Game-winning goals (Highest Priority)
        if is_game_winner:
            score += 10

        # Comeback & Clutch Situations
        is_home_goal = scoring_team == home_team
        scoring_team_score = home_score if is_home_goal else away_score
        opponent_score = away_score if is_home_goal else home_score
        prev_scoring_team_score = prev_home_score if is_home_goal else prev_away_score
        prev_opponent_score = prev_away_score if is_home_goal else prev_home_score

        # Tying goal
        if prev_scoring_team_score < prev_opponent_score and scoring_team_score == opponent_score:
            score += 7

        # Go-ahead goal
        if prev_scoring_team_score <= prev_opponent_score and scoring_team_score > opponent_score:
            score += 6

        # Insurance goal
        if period >= 3 and prev_scoring_team_score - prev_opponent_score == 1 and scoring_team_score - opponent_score >= 2:
            score += 2

        # Close game bonus
        score_diff = abs(scoring_team_score - opponent_score)
        if score_diff <= 1:
            score += 2

        # Late period goals
        def parse_time(time_str):
            if not time_str or ':' not in time_str:
                return 0
            parts = time_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])

        seconds_remaining = parse_time(time_remaining)

        if seconds_remaining > 0 and seconds_remaining <= 120:
            score += 3

        if seconds_remaining > 0 and seconds_remaining <= 30:
            score += 2

        # Third period goals
        if period == 3 and not is_game_winner:
            score += 1

        # Overtime & Shootout
        if period > 3 or period_type == 'OT':
            score += 5

        if period_type == 'SO':
            score += 3

        # Strength situations
        if strength == 'powerplay' or goal_modifier == 'power-play':
            score += 1

        if strength == 'shorthanded' or goal_modifier == 'short-handed':
            score += 4

        # Special goal types
        if goal_modifier == 'penalty-shot':
            score += 3

        if goal_modifier == 'empty-net':
            score -= 1
            if score < 1:
                score = 1

        # First goal of game
        if (home_score == 1 and away_score == 0) or (home_score == 0 and away_score == 1):
            score += 1

        return score

    def generate_interest_tags(
        self,
        scoring_team: str,
        opponent: str,
        scoring_player: Dict[str, Any],
        details: Dict[str, Any],
        play: Dict[str, Any],
        is_game_winner: bool,
        is_piling_on: bool,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate interest tags for topic-based filtering"""
        tags = []

        home_score = context.get('homeScore', 0)
        away_score = context.get('awayScore', 0)
        prev_home_score = context.get('prevHomeScore', 0)
        prev_away_score = context.get('prevAwayScore', 0)
        is_home_goal = context.get('isHomeGoal', False)
        time_remaining = context.get('timeRemaining')

        # Team tags
        tags.append(f"team:{scoring_team}")
        tags.append(f"opponent:{opponent}")

        # Player tag
        player_id = scoring_player.get('playerId')
        if player_id and str(player_id) != 'unknown':
            tags.append(f"player:{player_id}")

        # Shot type tag
        shot_type = details.get('shotType', 'unknown')
        tags.append(f"shot:{shot_type}")

        # Goal type tags
        goal_type = details.get('goalModifier')
        if goal_type and goal_type != 'even-strength':
            tags.append(f"goal:{goal_type}")

        # Strength tags
        strength = details.get('strength', 'even')
        if strength == 'shorthanded':
            tags.append('shorthanded')
        if strength == 'powerplay':
            tags.append('powerplay')

        # Special situation tags
        if is_game_winner:
            tags.append('game-winner')
        if is_piling_on:
            tags.append('piling-on')

        period = play.get('periodDescriptor', {}).get('number', 0)
        if period > 3:
            tags.append('overtime')

        period_type = play.get('periodDescriptor', {}).get('periodType')
        if period_type == 'SO':
            tags.append('shootout')
        if period_type == 'OT':
            tags.append('overtime')

        if goal_type == 'empty-net':
            tags.append('empty-net')
        if goal_type == 'penalty-shot':
            tags.append('penalty-shot')

        # Comeback & Clutch tags
        scoring_team_score = home_score if is_home_goal else away_score
        opponent_score = away_score if is_home_goal else home_score
        prev_scoring_team_score = prev_home_score if is_home_goal else prev_away_score
        prev_opponent_score = prev_away_score if is_home_goal else prev_home_score

        # Tying goal
        if prev_scoring_team_score < prev_opponent_score and scoring_team_score == opponent_score:
            tags.append('tying-goal')
            tags.append('comeback')

        # Go-ahead goal
        if prev_scoring_team_score <= prev_opponent_score and scoring_team_score > opponent_score:
            tags.append('go-ahead-goal')
            tags.append('comeback')

        # Close game
        if abs(scoring_team_score - opponent_score) <= 1:
            tags.append('close-game')

        # First goal
        if (home_score == 1 and away_score == 0) or (home_score == 0 and away_score == 1):
            tags.append('first-goal')

        # Late period tags
        if time_remaining:
            def parse_time(time_str):
                if ':' not in time_str:
                    return 0
                parts = time_str.split(':')
                return int(parts[0]) * 60 + int(parts[1])

            seconds_remaining = parse_time(time_remaining)

            if seconds_remaining <= 120:
                tags.append('late-period')

            if seconds_remaining <= 30:
                tags.append('buzzer-beater')

        # Third period tag
        if period == 3:
            tags.append('third-period')

        # Period tag
        tags.append(f"period:{period}")

        # Matchup tag
        tags.append(f"matchup:{scoring_team}-vs-{opponent}")

        return tags

    def generate_filter_tags(
        self,
        scoring_team: str,
        scoring_player: Dict[str, Any]
    ) -> List[str]:
        """Generate filter tags for server-side filtering"""
        tags = []

        # Team tricode tag
        tags.append(scoring_team)

        # Player ID tag
        player_id = scoring_player.get('playerId')
        if player_id and str(player_id) != 'unknown':
            tags.append(str(player_id))

        return tags

    async def upload_goals_with_collections(
        self,
        goals_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Upload goals using Collections

        Args:
            goals_data: List of goal data with activities and collection objects

        Returns:
            Upload statistics
        """
        uploaded = 0
        failed = 0

        for goal_data in goals_data:
            goal_object = goal_data['goalObject']
            activity = goal_data['activity']
            goal_id = goal_data['goalId']

            try:
                # Store goal in Collections (always upsert)
                self.stream_client.collections.upsert('goals', [
                    {
                        'id': goal_id,
                        'data': goal_object
                    }
                ])

                # Post to team-specific feed
                team_feed = self.stream_client.feed('goals', activity['scoring_team'])
                team_feed.add_activity(activity)

                # Post to central NHL feed
                nhl_feed = self.stream_client.feed('goals', 'nhl')
                nhl_feed.add_activity(activity)

                uploaded += 1

                # Rate limiting: pause 0.5 seconds between inserts
                await asyncio.sleep(0.5)

            except Exception as e:
                error_msg = str(e)
                if 'duplicate' not in error_msg.lower():
                    print(f"   ❌ Failed {goal_id}: {error_msg}")
                    failed += 1
                # Silently skip duplicates

        return {
            'uploaded': uploaded,
            'failed': failed
        }


async def main():
    """Main entry point for cron job"""
    print("\n" + "=" * 60)
    print("🏒 NHL GOALS SCRAPER - CRON JOB")
    print("=" * 60)

    # Initialize clients
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

        print("\n✅ Scrape completed successfully")
        print(f"📊 Summary: {json.dumps(summary, indent=2)}")

    except Exception as e:
        print(f"\n❌ Scrape failed: {str(e)}")
        raise
    finally:
        await scraper.close()
        await s3_storage.close()


if __name__ == '__main__':
    asyncio.run(main())
