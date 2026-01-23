# NHL Goals Scraper - Quick Start Guide

Get the scraper running in 5 minutes!

## 1. Install Dependencies (30 seconds)

```bash
cd backend
pip install -r requirements.txt
```

## 2. Configure Environment (1 minute)

Create `.env` file in the **project root** (one level up from `backend/`):

```bash
# Copy example
cp .env.example .env

# Edit with your values
STREAM_API_KEY=your_api_key_here
STREAM_API_SECRET=your_api_secret_here
STREAM_APP_ID=your_app_id_here
S3_BASE_URL=https://s3.foreverflow.click/api/hockeyGoals
S3_ENABLED=true
```

## 3. Test It (2 minutes)

```bash
# Quick test - scrape yesterday's games
cd backend
python -m test_scraper

# Full test suite
python -m test_scraper --all
```

Expected output:
```
🧪 Testing NHL Scraper with date: 2026-01-22
============================================================
✅ Environment variables OK
✅ GetStream client initialized
✅ S3 storage client initialized
✅ NHL scraper initialized
✅ S3 connection OK
📊 TEST RESULTS
Goals found: 15
Successfully uploaded: 15
✅ Test PASSED
```

## 4. Set Up Cron Job (1 minute)

```bash
# Make script executable
chmod +x backend/run_scraper_cron.sh

# Edit crontab
crontab -e

# Add this line (runs daily at 6 AM)
0 6 * * * /full/path/to/Stream.io/backend/run_scraper_cron.sh
```

Replace `/full/path/to/Stream.io` with your actual project path!

**To find your full path:**
```bash
cd /path/to/Stream.io/backend
pwd
# Copy the output and use it in crontab
```

## 5. Verify It's Working (30 seconds)

### Check Logs
```bash
# View latest log
tail -f backend/logs/scraper_*.log
```

### Check Progress in S3
```bash
curl https://s3.foreverflow.click/api/hockeyGoals/scrape_progress.json
```

Expected response:
```json
{
  "completed_dates": ["2026-01-20", "2026-01-21", "2026-01-22"],
  "failed_dates": [],
  "last_updated": "2026-01-23T06:00:00Z",
  "stats": {
    "totalGoals": 245
  }
}
```

## That's It! 🎉

The scraper will now run automatically every day at 6 AM.

---

## Common Cron Schedules

**Every 6 hours:**
```cron
0 */6 * * * /path/to/Stream.io/backend/run_scraper_cron.sh
```

**Twice daily (6 AM and 6 PM):**
```cron
0 6,18 * * * /path/to/Stream.io/backend/run_scraper_cron.sh
```

**Every day at midnight:**
```cron
0 0 * * * /path/to/Stream.io/backend/run_scraper_cron.sh
```

---

## Manual Run

Want to run it manually instead of cron?

```bash
cd backend
python -m app.nhl_scraper_cron
```

Or use the shell script:
```bash
cd backend
./run_scraper_cron.sh
```

---

## Programmatic Usage

Want to integrate it into your own Python code?

```python
import asyncio
from app.nhl_scraper_cron import NHLScraperCron
from app.s3_storage import S3Storage
from app.config import settings
from stream.client import StreamClient as GetStreamClient

async def main():
    # Initialize
    stream_client = GetStreamClient(
        api_key=settings.STREAM_API_KEY,
        api_secret=settings.STREAM_API_SECRET,
        app_id=settings.STREAM_APP_ID
    )
    s3_storage = S3Storage()
    scraper = NHLScraperCron(stream_client, s3_storage)

    try:
        # Scrape from last date to today
        summary = await scraper.scrape_to_today()
        print(f"✅ Scraped {summary['total_goals']} goals")
    finally:
        await scraper.close()
        await s3_storage.close()

asyncio.run(main())
```

See `example_usage.py` for more examples!

---

## Troubleshooting

### Cron job not running?

1. **Check cron is active:**
   ```bash
   # macOS
   sudo launchctl list | grep cron

   # Linux
   sudo systemctl status cron
   ```

2. **Check script permissions:**
   ```bash
   ls -la backend/run_scraper_cron.sh
   # Should show: -rwxr-xr-x (executable)
   ```

3. **Use absolute paths in crontab** (not `~/` or relative paths)

4. **Test script manually first:**
   ```bash
   /full/path/to/Stream.io/backend/run_scraper_cron.sh
   ```

5. **Check cron logs:**
   ```bash
   # macOS
   log show --predicate 'process == "cron"' --last 1h

   # Linux
   grep CRON /var/log/syslog
   ```

### S3 connection failed?

- Verify `S3_BASE_URL` in `.env`
- Test connectivity: `curl https://s3.foreverflow.click/api/hockeyGoals/scrape_progress.json`

### GetStream upload failed?

- Verify `STREAM_API_KEY`, `STREAM_API_SECRET`, `STREAM_APP_ID` in `.env`
- Check GetStream dashboard for errors

### No goals found?

- Check if NHL API is accessible: `curl https://api-web.nhle.com/v1/schedule/2026-01-22`
- Verify the date has games scheduled (NHL season typically Oct-June)

---

## What Happens Automatically?

✅ Scraper runs on schedule (e.g., daily at 6 AM)
✅ Loads last completed date from S3
✅ Scrapes all dates from last date → today
✅ Uploads goals to GetStream Collections & Feeds
✅ Saves progress to S3
✅ Creates timestamped logs
✅ Keeps last 30 logs (auto-cleanup)
✅ Skips duplicate goals
✅ Tracks failed dates for retry

---

## Monitoring

### View Logs
```bash
# Latest log
tail -100 backend/logs/scraper_*.log

# Follow live
tail -f backend/logs/scraper_*.log

# Specific date
cat backend/logs/scraper_20260123_060000.log
```

### Check Progress
```bash
# Current progress
curl https://s3.foreverflow.click/api/hockeyGoals/scrape_progress.json

# Latest summary
curl https://s3.foreverflow.click/api/hockeyGoals/scrape_summary_$(date +%Y-%m-%d)_*.json
```

### Check GetStream
```python
from app.stream_client import stream_client

# Get recent goals
nhl_feed = stream_client.client.feed('goals', 'nhl')
activities = nhl_feed.get(limit=10, enrich=True)
print(f"Found {len(activities['results'])} recent goals")
```

---

## Need More Help?

- **Full Documentation**: `SCRAPER_CRON_README.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **Crontab Examples**: `CRONTAB_EXAMPLES.txt`
- **Code Examples**: `example_usage.py`
- **Test Suite**: `test_scraper.py`

---

## Next Steps

1. ✅ Set up cron job
2. ⏰ Wait for first run (or run manually)
3. 📊 Check logs to verify success
4. 🎯 Monitor progress in S3
5. 🏒 Query goals from GetStream feeds

Happy scraping! 🏒
