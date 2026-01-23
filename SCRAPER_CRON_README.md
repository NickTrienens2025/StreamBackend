# NHL Goals Scraper - Cron Job Setup

This document explains how to set up and use the Python NHL goals scraper as a cron job.

## Overview

The scraper (`nhl_scraper_cron.py`) automatically scrapes NHL goal data and stores it in GetStream Collections and Activity Feeds. It uses S3 for progress tracking, so it can resume from where it left off.

### Features

- **S3 Progress Tracking**: Stores progress in S3 (`scrape_progress.json`) to track completed/failed dates
- **Auto-Resume**: Automatically scrapes from last completed date to today
- **Game-Winning Goal Detection**: Calculates which goal won the game
- **Full Player Enrichment**: Pulls player data from roster (names, headshots, positions)
- **Brightcove Video Data**: Fetches video clip IDs from NHL mobile API
- **Advanced Ranking**: Scores goals by importance (game-winner, overtime, comeback situations)
- **Interest & Filter Tags**: Enables topic-based filtering and personalization

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root (one level up from `backend/`) with:

```bash
# GetStream Configuration
STREAM_API_KEY=your_api_key_here
STREAM_API_SECRET=your_api_secret_here
STREAM_APP_ID=your_app_id_here

# S3 Storage Configuration
S3_BASE_URL=https://s3.foreverflow.click/api/hockeyGoals
S3_ENABLED=true
```

### 3. Make Shell Script Executable

```bash
chmod +x backend/run_scraper_cron.sh
```

## Usage

### Manual Run

Run the scraper manually to test:

```bash
cd backend
python -m app.nhl_scraper_cron
```

Or use the shell script:

```bash
cd backend
./run_scraper_cron.sh
```

### Set Up Cron Job

To run the scraper automatically every day at 6 AM:

1. Edit your crontab:
   ```bash
   crontab -e
   ```

2. Add this line (adjust path to your project):
   ```cron
   0 6 * * * /path/to/Stream.io/backend/run_scraper_cron.sh
   ```

**Common Cron Schedules:**

- Every day at 6 AM: `0 6 * * *`
- Every 6 hours: `0 */6 * * *`
- Every day at midnight: `0 0 * * *`
- Twice daily (6 AM and 6 PM): `0 6,18 * * *`

### View Logs

Logs are stored in `backend/logs/`:

```bash
# View latest log
tail -f backend/logs/scraper_*.log

# View specific log
cat backend/logs/scraper_20260123_060000.log
```

The script automatically keeps only the last 30 log files.

## How It Works

### Progress Tracking

The scraper uses S3 to track progress:

```json
{
  "completed_dates": ["2026-01-20", "2026-01-21", "2026-01-22"],
  "failed_dates": [],
  "last_updated": "2026-01-23T06:00:00Z",
  "stats": {
    "totalGoals": 245,
    "goalsByTeam": {},
    "goalsByPlayer": {}
  }
}
```

### Scraping Logic

1. **Load Progress**: Reads `scrape_progress.json` from S3
2. **Determine Date Range**: Finds last completed date, scrapes to today
3. **Process Each Date**:
   - Fetch NHL schedule for that date
   - For each game:
     - Get play-by-play data
     - Build roster lookup for player names
     - Fetch brightcove video data
     - Calculate game-winning goal
     - Convert goals to Collections + Activities
     - Upload to GetStream
4. **Update Progress**: Marks date as completed in S3
5. **Save Summary**: Stores summary stats in S3

### Data Structure

Each goal is stored as:

- **Collection Object** (`goals` collection): Full goal data with all details
- **Team Feed Activity** (`goals:TEAM`): Activity in team-specific feed
- **Central Feed Activity** (`goals:nhl`): Activity in league-wide feed

### Rate Limiting

- 100ms delay between game requests
- 500ms delay between GetStream uploads

## API Methods

### `scrape_to_today()`

Scrapes from last completed date to today.

```python
summary = await scraper.scrape_to_today()
# Returns: {
#   'date_range': '2026-01-20 to 2026-01-23',
#   'dates_processed': 3,
#   'total_goals': 45,
#   'total_uploaded': 45,
#   'total_failed': 0
# }
```

### `scrape_date_range(start_date, end_date)`

Scrapes a specific date range.

```python
summary = await scraper.scrape_date_range('2026-01-01', '2026-01-31')
```

## Monitoring

### Check Progress

Read the progress file from S3:

```bash
curl https://s3.foreverflow.click/api/hockeyGoals/scrape_progress.json
```

### Check Summaries

Summaries are saved after each run:

```bash
curl https://s3.foreverflow.click/api/hockeyGoals/scrape_summary_2026-01-23_06-00-00.json
```

### View Recent Logs

```bash
# Last 100 lines of latest log
tail -100 backend/logs/scraper_*.log | head -100

# Follow live scraping
tail -f backend/logs/scraper_$(date +%Y%m%d)*.log
```

## Troubleshooting

### Issue: No goals found

- Check if NHL API is accessible: `curl https://api-web.nhle.com/v1/schedule/2026-01-22`
- Verify the date has games scheduled

### Issue: S3 write failed

- Check S3_BASE_URL in .env
- Verify S3 endpoint is accessible: `curl https://s3.foreverflow.click/api/hockeyGoals/scrape_progress.json`

### Issue: GetStream upload failed

- Verify STREAM_API_KEY, STREAM_API_SECRET, STREAM_APP_ID in .env
- Check GetStream dashboard for errors

### Issue: Cron job not running

- Check cron logs: `grep CRON /var/log/syslog` (Linux) or `log show --predicate 'process == "cron"' --last 1h` (macOS)
- Verify script has execute permissions: `ls -la backend/run_scraper_cron.sh`
- Use absolute paths in crontab

## Testing

Test the scraper with a specific date:

```python
import asyncio
from app.nhl_scraper_cron import NHLScraperCron
from app.s3_storage import S3Storage
from app.config import settings
from stream.client import StreamClient

async def test():
    stream_client = StreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )
    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    # Test single date
    summary = await scraper.scrape_date_range('2026-01-22', '2026-01-22')
    print(summary)

    await scraper.close()
    await s3_storage.close()

asyncio.run(test())
```

## Performance

### Timing Estimates

- Single game: ~2-5 seconds (including API calls and uploads)
- Full day (10-15 games): ~30-60 seconds
- Historical month: ~20-30 minutes

### Resource Usage

- Memory: ~50-100 MB
- Network: Depends on number of goals (each upload is ~5-10 KB)
- S3 Storage: ~1-2 KB per date in progress file

## Architecture

```
┌─────────────────┐
│  Cron Scheduler │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  run_scraper_cron.sh│
│  (Shell Script)     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────┐
│  nhl_scraper_cron.py    │
│  (Python Scraper)       │
│                         │
│  ┌─────────────────┐    │
│  │ Load Progress   │    │
│  │ from S3         │    │
│  └────────┬────────┘    │
│           │             │
│  ┌────────▼────────┐    │
│  │ Scrape Date     │    │
│  │ Range           │    │
│  └────────┬────────┘    │
│           │             │
│  ┌────────▼────────┐    │
│  │ Process Games   │    │
│  └────────┬────────┘    │
│           │             │
│  ┌────────▼────────┐    │
│  │ Upload to       │    │
│  │ GetStream       │    │
│  └────────┬────────┘    │
│           │             │
│  ┌────────▼────────┐    │
│  │ Save Progress   │    │
│  │ to S3           │    │
│  └─────────────────┘    │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│  logs/scraper_*.log     │
│  (Output Logs)          │
└─────────────────────────┘
```

## License

See main project LICENSE file.
