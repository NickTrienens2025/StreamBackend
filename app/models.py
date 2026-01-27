"""
Request/Response models for API endpoints
Standardized models for consistency across all endpoints
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any


class ImpressionRequest(BaseModel):
    """
    Track an impression (view) of an activity

    Fields accept both snake_case and camelCase for iOS compatibility
    """
    user_id: Optional[str] = Field(
        None,
        description="User ID (email allowed, will be sanitized). Also accepts 'userId'."
    )
    userId: Optional[str] = Field(
        None,
        description="User ID in camelCase format (iOS compatibility)"
    )
    activity_id: Optional[str] = Field(
        None,
        description="Activity UUID from GetStream (activity.id field). Also accepts 'activityId'."
    )
    activityId: Optional[str] = Field(
        None,
        description="Activity ID in camelCase format (iOS compatibility)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata (team, player_id, goal_type, etc.)"
    )

    def get_user_id(self) -> str:
        """Get user_id from either format"""
        return self.user_id or self.userId or "unknown"

    def get_activity_id(self) -> str:
        """Get activity_id from either format"""
        return self.activity_id or self.activityId or "unknown"

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "ntrienens@nhl.com",
                "activity_id": "b227dc00-fb1f-11f0-8080-8001429e601f",
                "metadata": {
                    "team": "CGY",
                    "player_id": "8477018",
                    "goal_type": "go-ahead-goal"
                }
            }
        }


class ReactionRequest(BaseModel):
    """
    Add/remove a reaction (like, heart, etc.) to an activity

    IMPORTANT: activity_id MUST be the GetStream UUID (activity.id),
    NOT the foreign_id (goal:xxx).

    Fields accept both snake_case and camelCase for iOS compatibility.
    User IDs are auto-sanitized (emails work).
    """
    user_id: Optional[str] = Field(
        None,
        description="User ID (email allowed, will be auto-sanitized). Also accepts 'userId'."
    )
    userId: Optional[str] = Field(
        None,
        description="User ID in camelCase format (iOS compatibility)"
    )
    activity_id: Optional[str] = Field(
        None,
        description="Activity UUID from GetStream (activity.id field, NOT foreign_id). Also accepts 'activityId'.",
        examples=["b227dc00-fb1f-11f0-8080-8001429e601f"]
    )
    activityId: Optional[str] = Field(
        None,
        description="Activity ID in camelCase format (iOS compatibility)"
    )
    kind: str = Field(
        default="like",
        description="Reaction type: 'like', 'heart', 'comment', etc."
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional additional data for the reaction"
    )

    def get_user_id(self) -> str:
        """Get user_id from either format"""
        return self.user_id or self.userId or "unknown"

    def get_activity_id(self) -> str:
        """Get activity_id from either format"""
        return self.activity_id or self.activityId or "unknown"

    @field_validator('kind')
    @classmethod
    def validate_kind(cls, v: str) -> str:
        """Validate reaction kind"""
        allowed = ['like', 'heart', 'love', 'comment', 'share', 'save']
        if v not in allowed:
            # Still allow it, just warn
            print(f"⚠️  Unusual reaction kind: {v}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "ntrienens@nhl.com",
                "activity_id": "b227dc00-fb1f-11f0-8080-8001429e601f",
                "kind": "like"
            }
        }


class ReactionResponse(BaseModel):
    """Standard response for reaction operations"""
    success: bool
    message: Optional[str] = None
    reaction: Optional[Dict[str, Any]] = None


class ImpressionResponse(BaseModel):
    """Standard response for impression tracking"""
    success: bool
    message: str


class ErrorDetail(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    help: Optional[str] = None
