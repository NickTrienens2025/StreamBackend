# Startup Scraper

## Overview

The backend automatically runs the goal scraper when the service starts up. This ensures your feed always has the latest data without manual intervention.

## How It Works

1. **Service Starts** → Backend starts up
2. **Background Task** → Scraper runs in background (non-blocking)
3. **Check Recent Days** → Scrapes last 3 days for new goals
4. **Update Feed** → Uploads any new goals to GetStream
5. **Save Status** → Stores run status in S3

## Status Tracking

### Current Status File
**Location**: `scraper_startup_status.json` in S3

Contains the most recent startup run:
```json
{
  "started_at": "2026-01-27T10:00:00Z",
  "status": "completed",
  "completed_at": "2026-01-27T10:02:15Z",
  "days_back": 3,
  "error": null,
  "results": {
    "checked": 3,
    "newGoals": 15,
    "uploaded": 15,
    "daysCompleted": 2,
    "daysInProgress": 1
  }
}
```

### History File
**Location**: `scraper_startup_history.json` in S3

Keeps the last 50 startup runs:
```json
{
  "runs": [
    {
      "started_at": "2026-01-27T10:00:00Z",
      "status": "completed",
      "results": {...}
    },
    {
      "started_at": "2026-01-27T08:00:00Z",
      "status": "completed",
      "results": {...}
    }
  ],
  "last_updated": "2026-01-27T10:02:15Z"
}
```

## API Endpoints

### Get Current Status

```bash
GET /api/v1/scraper/startup-status
```

Returns the status of the most recent startup scraper run.

**Response:**
```json
{
  "success": true,
  "status": {
    "started_at": "2026-01-27T10:00:00Z",
    "status": "completed",
    "completed_at": "2026-01-27T10:02:15Z",
    "days_back": 3,
    "results": {
      "checked": 3,
      "newGoals": 15,
      "uploaded": 15
    }
  }
}
```

### Get Startup History

```bash
GET /api/v1/scraper/startup-history
```

Returns the last 50 startup scraper runs.

**Response:**
```json
{
  "success": true,
  "runs": [
    {
      "started_at": "2026-01-27T10:00:00Z",
      "status": "completed",
      "results": {...}
    }
  ],
  "last_updated": "2026-01-27T10:02:15Z"
}
```

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# Enable/disable startup scraper
STARTUP_SCRAPER_ENABLED=true

# Number of days to check on startup
STARTUP_SCRAPER_DAYS_BACK=3
```

### Disable Startup Scraper

To disable the automatic scraper on startup:

```env
STARTUP_SCRAPER_ENABLED=false
```

Or set it in your deployment environment.

## Status Values

- **`running`** - Scraper is currently running
- **`completed`** - Scraper finished successfully
- **`failed`** - Scraper encountered an error

## Benefits

✅ **Always Fresh Data** - Feed is up-to-date when users open the app
✅ **No Manual Intervention** - Runs automatically on each deployment/restart
✅ **Non-Blocking** - Runs in background, doesn't delay startup
✅ **Trackable** - Status stored in S3 for monitoring
✅ **Configurable** - Can be disabled or adjusted per environment

## Use Cases

### Development
```env
# Check only 1 day to speed up local development
STARTUP_SCRAPER_DAYS_BACK=1
```

### Production
```env
# Check last 3 days to catch any missed games
STARTUP_SCRAPER_DAYS_BACK=3
```

### Staging
```env
# Disable scraper in staging
STARTUP_SCRAPER_ENABLED=false
```

## Monitoring

### Check if scraper is running:

```bash
curl http://localhost:8000/api/v1/scraper/startup-status
```

### View logs:

The scraper outputs to stdout during startup:

```
============================================================
🏒 NHL Goals Backend Starting Up
============================================================

🚀 Starting up - checking for new goals (last 3 days)...

📅 2026-01-25: Already complete, skipping
📅 2026-01-26: Already complete, skipping
📅 2026-01-27: Checking...
  🎮 Games: 10 total, 3 finished, 2 live, 5 upcoming
  ⚽ Found 7 goals
  📤 Uploading to GetStream...
  ✅ Uploaded: 7, Failed: 0
  ⏳ Day marked as IN PROGRESS (2 live, 5 upcoming)

✅ Startup scraper completed: 7 new goals found

✅ Server ready - scraper running in background (checking last 3 days)
============================================================
```

## Integration Example

### Check startup status in your app:

```javascript
async function checkBackendStatus() {
  const response = await fetch('http://api.example.com/api/v1/scraper/startup-status');
  const data = await response.json();

  if (data.status.status === 'completed') {
    console.log(`Backend ready: ${data.status.results.newGoals} new goals loaded`);
  } else if (data.status.status === 'running') {
    console.log('Backend is loading latest goals...');
  }
}
```

### Swift Example:

```swift
struct StartupStatus: Codable {
    let success: Bool
    let status: ScraperStatus
}

struct ScraperStatus: Codable {
    let startedAt: String
    let status: String  // "running", "completed", "failed"
    let completedAt: String?
    let results: ScraperResults?

    enum CodingKeys: String, CodingKey {
        case startedAt = "started_at"
        case status
        case completedAt = "completed_at"
        case results
    }
}

struct ScraperResults: Codable {
    let newGoals: Int
    let uploaded: Int
}

func checkStartupStatus() async throws -> StartupStatus {
    let url = URL(string: "\(apiBase)/scraper/startup-status")!
    let (data, _) = try await URLSession.shared.data(from: url)
    return try JSONDecoder().decode(StartupStatus.self, from: data)
}
```

## Deployment Considerations

### Docker

The scraper runs on container start. No special configuration needed.

### Kubernetes

If using multiple replicas, each pod will run the scraper on startup. This is safe because:
- GetStream uses `foreign_id` to prevent duplicates
- S3 progress tracking prevents re-scraping completed dates
- Multiple scrapes are idempotent

### Serverless (AWS Lambda, etc.)

For serverless deployments, you may want to disable the startup scraper and instead:
- Use a scheduled cron job to run the scraper
- Call the `/scraper/check-for-new-goals` endpoint directly

```env
# Disable for serverless
STARTUP_SCRAPER_ENABLED=false
```

## Troubleshooting

### Scraper not running

1. Check configuration:
```bash
echo $STARTUP_SCRAPER_ENABLED
```

2. Check logs for startup messages

3. Verify S3 connectivity:
```bash
curl http://localhost:8000/api/v1/storage/progress
```

### Scraper failing

Check the status endpoint:
```bash
curl http://localhost:8000/api/v1/scraper/startup-status
```

Look for the `error` field:
```json
{
  "status": "failed",
  "error": "Connection timeout to NHL API"
}
```

### Startup taking too long

Reduce the days to check:
```env
STARTUP_SCRAPER_DAYS_BACK=1
```

Or disable it for faster startup:
```env
STARTUP_SCRAPER_ENABLED=false
```

## Best Practices

1. **Enable in Production** - Always have fresh data
2. **Monitor Status** - Check the status endpoint in your monitoring
3. **Review History** - Look at past runs to spot patterns
4. **Configure Per Environment** - Adjust based on needs
5. **Non-Critical** - App works even if scraper fails

The scraper runs in the background and doesn't block your application from starting. Users can start using the app immediately while the scraper updates the feed in the background.
