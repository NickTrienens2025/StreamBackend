# Backend Deployment Guide

## Overview

This backend provides a FastAPI server with endpoints to:
- Query GetStream Activity Feeds
- Check for new NHL goals on-demand
- Only mark days as complete when all games are finished
- Get game status and scraper progress

## Quick Start

### Local Development

```bash
cd backend
./start.sh
```

The server will start on `http://localhost:8000`

### Manual Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# GetStream Configuration
STREAM_API_KEY=your_api_key
STREAM_API_SECRET=your_api_secret
STREAM_APP_ID=your_app_id

# S3 Storage
S3_BASE_URL=https://s3.foreverflow.click/api/hockeyGoals

# API Configuration
API_PREFIX=/api/v1
ALLOWED_ORIGINS=*
DEBUG=true
```

## API Endpoints

### Scraper Endpoints (NEW)

#### POST `/api/v1/scraper/check-for-new-goals`

Check for new NHL goals and upload them to GetStream. Only marks days as complete when all games are finished.

**Call this endpoint when your app starts the feed experience** to ensure latest data is available.

**Query Parameters:**
- `days_back` (int, default: 3) - Number of days to look back (1-7)
- `force_refresh` (bool, default: false) - Force re-scrape of completed days

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/scraper/check-for-new-goals?days_back=3"
```

**Response:**
```json
{
  "success": true,
  "message": "Goal check completed",
  "results": {
    "checked": 3,
    "newGoals": 42,
    "uploaded": 42,
    "daysCompleted": 2,
    "daysInProgress": 1,
    "details": [...]
  }
}
```

#### GET `/api/v1/scraper/game-status/{date}`

Check if all games on a specific date are finished.

**Example:**
```bash
curl "http://localhost:8000/api/v1/scraper/game-status/2026-01-27"
```

**Response:**
```json
{
  "success": true,
  "date": "2026-01-27",
  "status": {
    "all_finished": false,
    "total_games": 10,
    "finished_games": 3,
    "live_games": 2,
    "future_games": 5,
    "games": [...]
  }
}
```

### Feed Endpoints

#### GET `/api/v1/feeds/{feed_id}/activities`

Get activities from a specific feed (team or central).

**Example:**
```bash
curl "http://localhost:8000/api/v1/feeds/nhl/activities?limit=20"
```

#### GET `/api/v1/activities/filter`

Filter activities by tags.

**Example:**
```bash
curl "http://localhost:8000/api/v1/activities/filter?tag=game-winner&limit=50"
```

#### GET `/api/v1/activities/filters/options`

Get available filter options for frontend.

## Integration with Your App

### On App Start

When your app starts the feed experience, call the check endpoint:

```javascript
// App startup - check for new goals
async function initializeFeed() {
  try {
    const response = await fetch('http://localhost:8000/api/v1/scraper/check-for-new-goals?days_back=3', {
      method: 'POST'
    });

    const data = await response.json();
    console.log(`Found ${data.results.newGoals} new goals`);

    // Now load the feed
    loadFeedData();
  } catch (error) {
    console.error('Failed to check for new goals:', error);
  }
}
```

### Swift/iOS Example

```swift
func checkForNewGoals() async {
    let url = URL(string: "https://your-backend.com/api/v1/scraper/check-for-new-goals?days_back=3")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"

    do {
        let (data, _) = try await URLSession.shared.data(for: request)
        let result = try JSONDecoder().decode(ScraperResult.self, from: data)
        print("Found \(result.results.newGoals) new goals")
    } catch {
        print("Error checking for goals: \(error)")
    }
}
```

## How It Works

### Smart Day Completion

The scraper checks the NHL API for game status:
- **FUT** (Future) - Game not started
- **LIVE** - Game in progress
- **FINAL/OFF** - Game completed

A day is only marked as **complete** when ALL games have finished. Days with live or future games remain **in-progress** and will be re-scraped on next check.

This ensures:
- ✅ Live games get their goals added as they happen
- ✅ No duplicate goals (uses foreign_id)
- ✅ Days aren't marked complete prematurely
- ✅ Efficient - only scrapes incomplete days

### Progress Tracking

Progress is stored in S3:
```json
{
  "completed_dates": ["2026-01-20", "2026-01-21", ...],
  "in_progress_dates": ["2026-01-27"],
  "last_updated": "2026-01-27T10:30:00Z",
  "stats": {
    "totalGoals": 1250
  }
}
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t nhl-backend .
docker run -p 8000:8000 --env-file .env nhl-backend
```

### Render.com

Use the included `render.yaml`:

```yaml
services:
  - type: web
    name: nhl-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Railway.app

```bash
railway link
railway up
```

## Testing

### Test the on-demand scraper directly:

```bash
cd backend
python -m app.scraper_on_demand --days=2
```

### Test with force refresh:

```bash
python -m app.scraper_on_demand --days=2 --force
```

## Monitoring

- Health check: `GET /health`
- API docs: `http://localhost:8000/docs` (Swagger UI)
- Scraper status: `GET /api/v1/storage/progress`

## Troubleshooting

### "Module not found" errors

Make sure you're in the virtual environment:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### S3 connection issues

Check your `S3_BASE_URL` environment variable:
```bash
echo $S3_BASE_URL
```

### No goals found

- Check if games are scheduled for that date
- Verify the NHL API is accessible
- Check scraper logs for errors

## Support

For issues or questions, check the logs or test the scraper directly with the Python module.
