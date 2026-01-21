# GetStream Activity Feeds Backend API

Platform-agnostic Python backend for GetStream Activity Feeds. Provides REST API endpoints for querying feeds, filtering activities, and generating client tokens.

## Features

- ✅ **FastAPI** - Modern, fast Python web framework
- ✅ **GetStream SDK** - Official Stream Python client
- ✅ **Environment-based config** - All settings via environment variables
- ✅ **Docker ready** - Containerized for easy deployment
- ✅ **Render ready** - One-click deployment to Render
- ✅ **CORS enabled** - Ready for frontend apps
- ✅ **Health checks** - Built-in monitoring endpoints
- ✅ **Auto documentation** - Swagger/OpenAPI docs at `/docs`

## Quick Start

### Local Development

1. **Clone and navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your GetStream credentials
   ```

5. **Run the server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access API**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

### Docker Development

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Access API**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs

## Environment Variables

Required environment variables (see `.env.example`):

```bash
# GetStream Configuration
STREAM_API_KEY=your_api_key
STREAM_API_SECRET=your_secret
STREAM_APP_ID=your_app_id

# Feed Configuration
DEFAULT_FEED_GROUP=goals      # Your feed group name
CENTRAL_FEED_ID=nhl          # Central feed ID

# API Configuration
API_PREFIX=/api/v1
ALLOWED_ORIGINS=*            # Comma-separated origins

# App Settings
DEBUG=false
DEFAULT_LIMIT=50
MAX_LIMIT=1000

# S3-Compatible Storage
S3_BASE_URL=https://s3.foreverflow.click/api/hockeyGoals
S3_ENABLED=true
```

## API Endpoints

### Health Check
```
GET /health
```
Returns API health status.

### Get Feed Activities
```
GET /api/v1/feeds/{feed_id}/activities
```
Get activities from a specific feed.

**Query Parameters:**
- `feed_group` - Feed group name (default: from config)
- `limit` - Number of activities (default: 50, max: 1000)
- `offset` - Pagination offset (default: 0)
- `enrich` - Enrich with collections (default: true)

**Example:**
```bash
curl http://localhost:8000/api/v1/feeds/nhl/activities?limit=10
```

### Get Recent Activities
```
GET /api/v1/activities/recent
```
Get recent activities from central feed.

**Query Parameters:**
- `feed_id` - Feed ID (default: from config)
- `limit` - Number of activities (default: 20)

**Example:**
```bash
curl http://localhost:8000/api/v1/activities/recent
```

### Filter Activities
```
GET /api/v1/activities/filter
```
Get activities with filtering.

**Query Parameters:**
- `tag` - Filter by interest tag (e.g., "game-winner")
- `filter_tag` - Filter by filter tag (e.g., "COL")
- `limit` - Number of activities

**Example:**
```bash
curl http://localhost:8000/api/v1/activities/filter?tag=game-winner&limit=20
```

### Get Feed Statistics
```
GET /api/v1/feeds/{feed_id}/stats
```
Get aggregated statistics for a feed.

**Example:**
```bash
curl http://localhost:8000/api/v1/feeds/nhl/stats
```

### Generate Feed Token
```
GET /api/v1/token/{feed_id}
```
Generate client-side feed token for frontend apps.

**Example:**
```bash
curl http://localhost:8000/api/v1/token/user123
```

### Get Collection Objects
```
GET /api/v1/collections/{collection_name}?ids=id1&ids=id2
```
Get objects from a GetStream collection.

**Example:**
```bash
curl "http://localhost:8000/api/v1/collections/goals?ids=goal123&ids=goal456"
```

### Get Scrape Progress
```
GET /api/v1/storage/progress
```
Get current scrape progress from S3 storage.

**Example:**
```bash
curl http://localhost:8000/api/v1/storage/progress
```

### List Scrape Summaries
```
GET /api/v1/storage/summaries
```
List all scrape summary files from S3 storage.

**Example:**
```bash
curl http://localhost:8000/api/v1/storage/summaries
```

### Get Storage Data
```
GET /api/v1/storage/{key}
```
Get any file from S3 storage by key.

**Example:**
```bash
curl http://localhost:8000/api/v1/storage/scrape_summary_2026-01-20.json
```

## Deployment

### Deploy to Render

1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/NickTrienens2025/StreamBackend.git
   git push -u origin main
   ```

2. **Connect to Render**
   - Go to https://render.com
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml` and deploy automatically

3. **Configure environment variables in Render dashboard**
   - `STREAM_API_KEY`
   - `STREAM_API_SECRET`
   - `STREAM_APP_ID`

4. **Access your deployed API**
   - URL: https://your-app-name.onrender.com
   - Docs: https://your-app-name.onrender.com/docs

### Deploy to Other Platforms

#### Heroku
```bash
heroku create your-app-name
heroku container:push web
heroku container:release web
```

#### Railway
```bash
railway init
railway up
```

#### Fly.io
```bash
fly launch
fly deploy
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py        # Package initialization
│   ├── main.py            # FastAPI app and routes
│   ├── config.py          # Environment configuration
│   ├── stream_client.py   # GetStream client wrapper
│   └── api.py             # API route handlers
├── Dockerfile             # Docker container definition
├── docker-compose.yml     # Docker Compose config
├── render.yaml            # Render deployment config
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Frontend Integration

### JavaScript/React Example

```javascript
// Fetch recent activities
const response = await fetch('http://localhost:8000/api/v1/activities/recent?limit=20');
const data = await response.json();
console.log(data.data); // Array of activities

// Filter by tag
const filtered = await fetch(
  'http://localhost:8000/api/v1/activities/filter?tag=game-winner&limit=10'
);
const gameWinners = await filtered.json();

// Get team-specific feed
const teamFeed = await fetch('http://localhost:8000/api/v1/feeds/COL/activities');
const teamData = await teamFeed.json();
```

### React Component Example

```jsx
import { useState, useEffect } from 'react';

function ActivityFeed({ feedId = 'nhl' }) {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchActivities() {
      const res = await fetch(
        `http://localhost:8000/api/v1/feeds/${feedId}/activities?limit=50`
      );
      const data = await res.json();
      setActivities(data.data);
      setLoading(false);
    }
    fetchActivities();
  }, [feedId]);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {activities.map(activity => (
        <div key={activity.id}>
          {/* Render activity */}
        </div>
      ))}
    </div>
  );
}
```

## Development

### Run tests
```bash
pytest
```

### Format code
```bash
black app/
```

### Lint code
```bash
flake8 app/
```

## Troubleshooting

### Port already in use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Docker issues
```bash
# Clean rebuild
docker-compose down -v
docker-compose up --build
```

### GetStream connection issues
- Verify API credentials in `.env`
- Check GetStream dashboard for app status
- Ensure feed groups exist in GetStream

## License

MIT

## Support

For issues and questions:
- GetStream Docs: https://getstream.io/activity-feeds/docs/
- FastAPI Docs: https://fastapi.tiangolo.com/
- GitHub Issues: https://github.com/NickTrienens2025/StreamBackend/issues
