"""
S3-Compatible Storage Client for Python
Uses s3.foreverflow.click/api/hockeyGoals/ for persistent storage
"""
import httpx
import json
from typing import Any, Optional, Dict
from app.config import settings


class S3Storage:
    """S3-compatible storage client"""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize S3 storage client"""
        self.base_url = base_url or settings.S3_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def write(self, key: str, data: Any) -> bool:
        """
        Write data to S3 storage

        Args:
            key: Storage key (filename)
            data: Data to store (dict, list, or string)

        Returns:
            Success status
        """
        try:
            url = f"{self.base_url}/{key}"

            # Convert data to JSON string if needed
            if isinstance(data, (dict, list)):
                body = json.dumps(data, indent=2)
            else:
                body = str(data)

            print(f"📤 Writing to S3: {key}")

            response = await self.client.put(
                url,
                content=body,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code not in [200, 201, 204]:
                raise Exception(f"S3 write failed: {response.status_code} {response.text}")

            print(f"✅ Successfully wrote to S3: {key}")
            return True

        except Exception as e:
            print(f"❌ S3 write error for {key}: {str(e)}")
            raise

    async def read(self, key: str, parse_json: bool = True) -> Optional[Any]:
        """
        Read data from S3 storage

        Args:
            key: Storage key (filename)
            parse_json: Whether to parse response as JSON

        Returns:
            Retrieved data or None if not found
        """
        try:
            url = f"{self.base_url}/{key}"

            print(f"📥 Reading from S3: {key}")

            response = await self.client.get(url)

            if response.status_code == 404:
                print(f"ℹ️  Key not found in S3: {key}")
                return None

            if response.status_code != 200:
                raise Exception(f"S3 read failed: {response.status_code} {response.text}")

            data = response.json() if parse_json else response.text
            print(f"✅ Successfully read from S3: {key}")
            return data

        except Exception as e:
            print(f"❌ S3 read error for {key}: {str(e)}")
            raise

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in S3 storage

        Args:
            key: Storage key (filename)

        Returns:
            True if exists
        """
        try:
            url = f"{self.base_url}/{key}"
            response = await self.client.head(url)
            return response.status_code == 200
        except:
            return False

    async def load_progress(self) -> Dict[str, Any]:
        """
        Load scrape progress from S3

        Returns:
            Progress data dictionary
        """
        try:
            data = await self.read('scrape_progress.json')
            if data:
                return data
        except Exception as e:
            print(f"⚠️  Could not load progress from S3: {str(e)}")

        # Return default progress structure
        return {
            'completed_dates': [],
            'failed_dates': [],
            'last_updated': None,
            'stats': {
                'totalGoals': 0,
                'goalsByTeam': {},
                'goalsByPlayer': {}
            }
        }

    async def save_progress(self, progress: Dict[str, Any]) -> None:
        """
        Save scrape progress to S3

        Args:
            progress: Progress data to save
        """
        from datetime import datetime
        progress['last_updated'] = datetime.utcnow().isoformat()
        await self.write('scrape_progress.json', progress)

    async def save_activities(self, activities: list, timestamp: str) -> None:
        """
        Save activities to S3

        Args:
            activities: List of activities
            timestamp: Timestamp for filename
        """
        key = f"nhl_goals_historical_{timestamp}.json"
        await self.write(key, activities)

    async def save_summary(self, summary: Dict[str, Any], timestamp: str) -> None:
        """
        Save scrape summary to S3

        Args:
            summary: Summary data
            timestamp: Timestamp for filename
        """
        key = f"scrape_summary_{timestamp}.json"
        await self.write(key, summary)

    async def list_summaries(self) -> list:
        """
        List all summary files (if bucket listing is supported)

        Returns:
            List of summary filenames
        """
        # Note: This assumes the S3 API supports listing
        # If not supported, this will need to be tracked separately
        try:
            response = await self.client.get(self.base_url)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return [item for item in data if item.startswith('scrape_summary_')]
        except:
            pass
        return []


# Singleton instance
s3_storage = S3Storage()
