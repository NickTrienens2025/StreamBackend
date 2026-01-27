# On-Demand NHL Goals Scraper

## Overview

The on-demand scraper checks for new NHL goals and only marks days as complete when all games are finished. This ensures live game data is captured without duplicates.

## Files Created

### Backend (Python)

1. **`app/scraper_on_demand.py`** - Core scraper logic
   - `check_for_new_goals()` - Main function to check and upload goals
   - `are_all_games_finished()` - Checks if all games on a date are done
   - `get_recent_dates()` - Gets dates to check

2. **`app/api.py`** - API endpoints (updated)
   - `POST /api/v1/scraper/check-for-new-goals` - Check for new goals
   - `GET /api/v1/scraper/game-status/{date}` - Get game status for a date

3. **`app/s3_storage.py`** - Storage (updated)
   - Added `in_progress_dates` to progress tracking

4. **`start.sh`** - Quick start script
5. **`DEPLOYMENT.md`** - Comprehensive deployment guide

## How to Use

### Start the Backend

```bash
cd backend
./start.sh
```

Server runs on `http://localhost:8000`

### Call from Your App

When your app starts the feed experience, call:

```bash
POST http://localhost:8000/api/v1/scraper/check-for-new-goals?days_back=3
```

### Response Example

```json
{
  "success": true,
  "message": "Goal check completed",
  "results": {
    "checked": 3,
    "newGoals": 15,
    "uploaded": 15,
    "daysCompleted": 2,
    "daysInProgress": 1,
    "details": [
      {
        "date": "2026-01-25",
        "status": "complete",
        "goals": 8,
        "games": {
          "all_finished": true,
          "total_games": 5,
          "finished_games": 5
        }
      },
      {
        "date": "2026-01-27",
        "status": "in_progress",
        "goals": 7,
        "games": {
          "all_finished": false,
          "total_games": 10,
          "finished_games": 3,
          "live_games": 2,
          "future_games": 5
        }
      }
    ]
  }
}
```

## Key Features

✅ **Only marks days complete when all games finish**
   - Days with live/future games stay "in-progress"
   - Automatically re-scraped on next check

✅ **No duplicates**
   - Uses `foreign_id` to prevent duplicate uploads
   - Safe to call multiple times

✅ **Efficient**
   - Only scrapes incomplete dates
   - Skip completed days (unless force refresh)

✅ **Game status tracking**
   - FUT (future) - not started
   - LIVE - in progress
   - FINAL/OFF - completed

## Integration Examples

### JavaScript/TypeScript

```javascript
async function loadFeed() {
  // Check for new goals first
  await fetch('http://localhost:8000/api/v1/scraper/check-for-new-goals', {
    method: 'POST'
  });

  // Then load feed
  const activities = await fetchActivities();
  renderFeed(activities);
}
```

### Swift

```swift
func initializeFeed() async {
    // Check for new goals
    let url = URL(string: "\(apiBase)/scraper/check-for-new-goals")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"

    try? await URLSession.shared.data(for: request)

    // Load feed
    await loadActivities()
}
```

### Python

```python
import httpx

async def initialize_feed():
    async with httpx.AsyncClient() as client:
        # Check for new goals
        response = await client.post(
            "http://localhost:8000/api/v1/scraper/check-for-new-goals",
            params={"days_back": 3}
        )

        # Load feed
        activities = await load_activities()
```

## Testing

### Test directly (CLI):

```bash
cd backend
python -m app.scraper_on_demand --days=2
```

### Test with cURL:

```bash
curl -X POST "http://localhost:8000/api/v1/scraper/check-for-new-goals?days_back=2"
```

### Check game status:

```bash
curl "http://localhost:8000/api/v1/scraper/game-status/2026-01-27"
```

## Progress Tracking

Progress stored in S3 at `scrape_progress.json`:

```json
{
  "completed_dates": ["2026-01-20", "2026-01-21", ...],
  "in_progress_dates": ["2026-01-27"],
  "stats": {
    "totalGoals": 1250
  },
  "last_updated": "2026-01-27T10:30:00Z"
}
```

## Deployment

Deploy to any Python hosting service:

- **Render.com** - Use `render.yaml`
- **Railway.app** - Auto-detects Python
- **Heroku** - Use `Procfile`
- **Docker** - Use `Dockerfile`

See `DEPLOYMENT.md` for detailed instructions.

## API Documentation

Full API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
