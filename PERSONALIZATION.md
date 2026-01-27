# Feed Personalization & Reactions

## Overview

The backend now supports full personalization with:
- ✅ **Reactions** (likes/hearts) with persistence
- ✅ **Impression tracking** (view analytics)
- ✅ **Engagement profiles** (user preferences)
- ✅ **Personalized feeds** with reaction state

## How It Works

### 1. Impression Tracking (Already Implemented)

Your iOS app already tracks views correctly! When an activity scrolls into view (60% visible), it calls:

```swift
POST /api/v1/analytics/impression
{
    "user_id": "user123",
    "activity_id": "goal:2025020826_123",
    "metadata": {
        "team": "CGY",
        "player_id": "8477018",
        "goal_type": "go-ahead-goal"
    }
}
```

**Storage**: `analytics/impressions_{user_id}.json` in S3

### 2. Reactions (Likes/Hearts)

#### Add a Like

```bash
POST /api/v1/reactions/add
{
    "user_id": "user123",
    "activity_id": "goal:2025020826_123",
    "kind": "like"
}
```

**Response:**
```json
{
    "success": true,
    "reaction": {
        "id": "reaction_abc123",
        "kind": "like",
        "activity_id": "goal:2025020826_123",
        "user_id": "user123",
        "created_at": "2026-01-27T10:00:00Z"
    }
}
```

#### Remove a Like

```bash
DELETE /api/v1/reactions/reaction_abc123
```

#### Check if User Liked an Activity

```bash
GET /api/v1/reactions/user/user123/activity/goal:2025020826_123?kind=like
```

**Response:**
```json
{
    "success": true,
    "user_id": "user123",
    "activity_id": "goal:2025020826_123",
    "has_reacted": true,
    "reaction": {
        "id": "reaction_abc123",
        "kind": "like"
    }
}
```

### 3. Personalized Feed with Reactions

#### Get Feed with User's Reaction State

```bash
GET /api/v1/feeds/nhl/personalized?user_id=user123&limit=50
```

**Response:**
```json
{
    "success": true,
    "feed": "goals:nhl",
    "user_id": "user123",
    "count": 50,
    "data": [
        {
            "id": "goal:2025020826_123",
            "actor": "team:CGY",
            "verb": "score",
            "object": "goal:2025020826_123",
            "scoring_player_name": "Mikael Backlund",
            "scoring_team": "CGY",

            // Reaction data
            "own_reactions": {
                "like": [
                    {
                        "id": "reaction_abc123",
                        "kind": "like",
                        "user_id": "user123",
                        "created_at": "2026-01-27T10:00:00Z"
                    }
                ]
            },
            "reaction_counts": {
                "like": 47
            }
        }
    ],
    "personalization": {
        "top_teams": [
            {"team": "CGY", "views": 25},
            {"team": "EDM", "views": 18}
        ],
        "total_views": 150
    }
}
```

## iOS Integration

### Step 1: Update StreamActivity Model

Add reactions fields to your `StreamActivity` model:

```swift
struct StreamActivity: Codable, Identifiable {
    let id: String
    let actor: String
    let verb: String
    let object: String

    // Existing fields...
    let scoringPlayerName: String
    let scoringTeam: String

    // NEW: Reaction fields
    let ownReactions: OwnReactions?
    let reactionCounts: ReactionCounts?

    enum CodingKeys: String, CodingKey {
        case id, actor, verb, object
        case scoringPlayerName = "scoring_player_name"
        case scoringTeam = "scoring_team"
        case ownReactions = "own_reactions"
        case reactionCounts = "reaction_counts"
    }
}

struct OwnReactions: Codable {
    let like: [Reaction]?
}

struct Reaction: Codable {
    let id: String
    let kind: String
    let userId: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, kind
        case userId = "user_id"
        case createdAt = "created_at"
    }
}

struct ReactionCounts: Codable {
    let like: Int?
}
```

### Step 2: Update Activity Header View

Replace the local state with backend data:

```swift
struct ActivityHeaderView: View {
    let activity: StreamActivity
    let userId: String
    @StateObject private var likeManager = LikeManager()

    // Compute from activity data
    private var isLiked: Bool {
        activity.ownReactions?.like?.isEmpty == false
    }

    private var likeCount: Int {
        activity.reactionCounts?.like ?? 0
    }

    var body: some View {
        HStack {
            // ... other header content ...

            // Like button
            Button(action: {
                Task {
                    await likeManager.toggleLike(
                        userId: userId,
                        activityId: activity.id,
                        currentReaction: activity.ownReactions?.like?.first
                    )
                }
            }) {
                HStack(spacing: 4) {
                    Image(systemName: isLiked ? "heart.fill" : "heart")
                        .foregroundColor(isLiked ? .red : .gray)

                    Text("\(likeCount)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
    }
}
```

### Step 3: Create Like Manager

```swift
@MainActor
class LikeManager: ObservableObject {
    private let apiBase = "http://localhost:8000/api/v1"

    func toggleLike(
        userId: String,
        activityId: String,
        currentReaction: Reaction?
    ) async {
        if let reaction = currentReaction {
            // Unlike - remove reaction
            await removeLike(reactionId: reaction.id)
        } else {
            // Like - add reaction
            await addLike(userId: userId, activityId: activityId)
        }
    }

    private func addLike(userId: String, activityId: String) async {
        let url = URL(string: "\(apiBase)/reactions/add")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "user_id": userId,
            "activity_id": activityId,
            "kind": "like"
        ]

        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                print("✅ Like added")
            }
        } catch {
            print("❌ Failed to add like: \(error)")
        }
    }

    private func removeLike(reactionId: String) async {
        let url = URL(string: "\(apiBase)/reactions/\(reactionId)")!
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                print("✅ Like removed")
            }
        } catch {
            print("❌ Failed to remove like: \(error)")
        }
    }
}
```

### Step 4: Use Personalized Feed Endpoint

Update your feed loading to use the personalized endpoint:

```swift
func loadPersonalizedFeed() async {
    let url = URL(string: "\(apiBase)/feeds/nhl/personalized?user_id=\(userId)&limit=50")!

    do {
        let (data, _) = try await URLSession.shared.data(from: url)
        let response = try JSONDecoder().decode(PersonalizedFeedResponse.self, from: data)

        self.activities = response.data

        // Optional: Use personalization data
        print("User's top team: \(response.personalization.topTeams.first?.team ?? "None")")

    } catch {
        print("❌ Failed to load personalized feed: \(error)")
    }
}

struct PersonalizedFeedResponse: Codable {
    let success: Bool
    let data: [StreamActivity]
    let personalization: PersonalizationData
}

struct PersonalizationData: Codable {
    let topTeams: [TeamPreference]
    let totalViews: Int

    enum CodingKeys: String, CodingKey {
        case topTeams = "top_teams"
        case totalViews = "total_views"
    }
}

struct TeamPreference: Codable {
    let team: String
    let views: Int
}
```

### Step 5: Update Impression Tracking (Optional Enhancement)

Add metadata to your impression tracking for better personalization:

```swift
func trackView(activityId: String) async {
    let url = URL(string: "\(apiBase)/analytics/impression")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    // Extract from activity
    let metadata: [String: Any] = [
        "team": activity.scoringTeam,
        "player_id": activity.scoringPlayerId,
        "goal_type": activity.interestTags.first { $0.contains("goal") } ?? ""
    ]

    let body: [String: Any] = [
        "user_id": userId,
        "activity_id": activityId,
        "metadata": metadata
    ]

    request.httpBody = try? JSONSerialization.data(withJSONObject: body)

    do {
        try await URLSession.shared.data(for: request)
    } catch {
        print("❌ Failed to track impression: \(error)")
    }
}
```

## How Reactions Work

### GetStream Reactions Flow

1. **Add Reaction** → Stored in GetStream reactions collection
2. **Query Feed** → Activities enriched with `own_reactions` and `reaction_counts`
3. **Display** → Show heart state and count from enriched data
4. **Toggle** → Add/remove reaction via API

### Data Structure

```
GetStream:
  Activities (goals feed)
    ├── Activity 1
    ├── Activity 2
    └── Activity 3

  Reactions (linked to activities)
    ├── user123 liked Activity 1
    ├── user456 liked Activity 1
    └── user123 liked Activity 3

S3 Storage:
  analytics/impressions_user123.json
    └── {
          "impressions": {
            "Activity 1": { "view_count": 5 },
            "Activity 2": { "view_count": 2 }
          }
        }
```

## Benefits

✅ **Persistent Likes** - Reactions saved in GetStream, not lost on app restart
✅ **Accurate Counts** - Real-time like counts from backend
✅ **Per-User State** - Each user sees their own like state
✅ **Personalization** - Feed learns user preferences from views
✅ **No Duplicates** - GetStream handles reaction uniqueness
✅ **Offline Support** - Can queue reactions and sync later

## Testing

### Test Reactions

```bash
# Like an activity
curl -X POST http://localhost:8000/api/v1/reactions/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "activity_id": "goal:2025020826_123",
    "kind": "like"
  }'

# Check if user liked it
curl http://localhost:8000/api/v1/reactions/user/test_user/activity/goal:2025020826_123

# Get personalized feed
curl "http://localhost:8000/api/v1/feeds/nhl/personalized?user_id=test_user&limit=10"
```

### Test Analytics

```bash
# Track impression
curl -X POST http://localhost:8000/api/v1/analytics/impression \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "activity_id": "goal:2025020826_123",
    "metadata": {
      "team": "CGY",
      "player_id": "8477018"
    }
  }'

# Get user profile
curl http://localhost:8000/api/v1/analytics/user/test_user/profile
```

## API Endpoints Summary

### Analytics
- `POST /api/v1/analytics/impression` - Track view
- `GET /api/v1/analytics/user/{user_id}/profile` - Get engagement profile
- `GET /api/v1/analytics/user/{user_id}/impressions` - Get all impressions

### Reactions
- `POST /api/v1/reactions/add` - Add like/reaction
- `DELETE /api/v1/reactions/{reaction_id}` - Remove reaction
- `GET /api/v1/reactions/activity/{activity_id}` - Get all reactions for activity
- `GET /api/v1/reactions/user/{user_id}/activity/{activity_id}` - Check user's reaction

### Personalized Feed
- `GET /api/v1/feeds/{feed_id}/personalized?user_id={user_id}` - Get feed with reactions

## Future Enhancements

- **Ranking Algorithm** - Sort feed by user preferences
- **Recommendation Engine** - Suggest goals based on viewing history
- **Collaborative Filtering** - "Users who liked this also liked..."
- **Real-time Updates** - WebSocket for live like counts
- **More Reaction Types** - comment, share, save

## Troubleshooting

### Likes not persisting

Check if `own_reactions` field is in the API response:
```bash
curl "http://localhost:8000/api/v1/feeds/nhl/personalized?user_id=user123&limit=1" | jq '.data[0].own_reactions'
```

### Counts not updating

Verify reaction was added:
```bash
curl "http://localhost:8000/api/v1/reactions/activity/goal:2025020826_123"
```

### No personalization data

Track some impressions first, then check profile:
```bash
curl "http://localhost:8000/api/v1/analytics/user/test_user/profile"
```

The personalization system is now fully functional and ready to integrate into your iOS app!
