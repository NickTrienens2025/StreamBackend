# API Requirements - Impressions & Reactions

## 📋 Overview

This document clearly defines what data format is expected for **all** impression and reaction endpoints.

## 🎯 Golden Rule

### Activity ID Format

**ALL endpoints require:**
- ✅ **Use `activity.id`** - GetStream's internal UUID
- ❌ **NOT `activity.foreign_id`** - Our custom ID

```
✅ Correct:   "b227dc00-fb1f-11f0-8080-8001429e601f"
❌ Wrong:     "goal:2025020829_576"
```

### User ID Format

**ALL endpoints accept:**
- ✅ Any string including emails
- ✅ Auto-sanitized on backend (`@` → `_at_`, `.` → `_`)

```
✅ Correct:   "ntrienens@nhl.com"
✅ Correct:   "user123"
✅ Correct:   "john_doe"
```

## 📡 Endpoints

### 1. Track Impression (View)

**Endpoint:** `POST /api/v1/analytics/impression`

**Purpose:** Track when a user views an activity (60% visible)

**Request:**
```json
{
  "user_id": "ntrienens@nhl.com",
  "activity_id": "b227dc00-fb1f-11f0-8080-8001429e601f",
  "metadata": {
    "team": "CGY",
    "player_id": "8477018",
    "goal_type": "go-ahead-goal"
  }
}
```

**Accepts both formats:**
- `user_id` or `userId`
- `activity_id` or `activityId`

**Response:**
```json
{
  "success": true,
  "message": "Impression tracked successfully"
}
```

### 2. Add Reaction (Like/Heart)

**Endpoints:**
- `POST /api/v1/reactions/add` (primary)
- `POST /api/v1/analytics/reaction` (legacy alias)

**Purpose:** Add a like/heart reaction to an activity

**Request:**
```json
{
  "user_id": "ntrienens@nhl.com",
  "activity_id": "b227dc00-fb1f-11f0-8080-8001429e601f",
  "kind": "like"
}
```

**Fields:**
- `user_id` or `userId` - Any string (required)
- `activity_id` or `activityId` - GetStream UUID (required)
- `kind` - "like", "heart", "love", etc. (default: "like")
- `data` - Optional additional data (optional)

**Response:**
```json
{
  "success": true,
  "message": "Reaction 'like' added successfully",
  "reaction": {
    "id": "reaction_abc123",
    "kind": "like",
    "activity_id": "b227dc00-fb1f-11f0-8080-8001429e601f",
    "user_id": "ntrienens_at_nhl_com"
  }
}
```

### 3. Remove Reaction

**Endpoint:** `DELETE /api/v1/reactions/{reaction_id}`

**Purpose:** Remove a previously added reaction

**Example:** `DELETE /api/v1/reactions/reaction_abc123`

### 4. Check User Reaction

**Endpoint:** `GET /api/v1/reactions/user/{user_id}/activity/{activity_id}`

**Purpose:** Check if a user has reacted to an activity

**Example:** `GET /api/v1/reactions/user/ntrienens@nhl.com/activity/b227dc00-fb1f-11f0-8080-8001429e601f?kind=like`

**Response:**
```json
{
  "success": true,
  "user_id": "ntrienens_at_nhl_com",
  "activity_id": "b227dc00-fb1f-11f0-8080-8001429e601f",
  "has_reacted": true,
  "reaction": {
    "id": "reaction_abc123",
    "kind": "like"
  }
}
```

## 📱 iOS Integration

### StreamActivity Model

Your model MUST include the `id` field (UUID):

```swift
struct StreamActivity: Codable, Identifiable {
    let id: String              // ✅ GetStream UUID - USE THIS
    let foreignId: String       // ❌ Custom ID - DON'T USE for reactions

    let actor: String
    let verb: String
    let object: String

    // Other fields...
    let scoringPlayerName: String
    let scoringTeam: String
    let scoringPlayerId: String

    // Reaction state
    let ownReactions: OwnReactions?
    let reactionCounts: ReactionCounts?

    enum CodingKeys: String, CodingKey {
        case id
        case foreignId = "foreign_id"
        case actor, verb, object
        case scoringPlayerName = "scoring_player_name"
        case scoringTeam = "scoring_team"
        case scoringPlayerId = "scoring_player_id"
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

### Track Impression (View)

```swift
func trackView(activity: StreamActivity, userEmail: String) async {
    let url = URL(string: "\(apiBase)/analytics/impression")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    let body: [String: Any] = [
        "user_id": userEmail,
        "activity_id": activity.id,  // ✅ Use UUID
        "metadata": [
            "team": activity.scoringTeam,
            "player_id": activity.scoringPlayerId,
            "goal_type": activity.interestTags?.first ?? ""
        ]
    ]

    request.httpBody = try? JSONSerialization.data(withJSONObject: body)

    do {
        let (_, response) = try await URLSession.shared.data(for: request)
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
            print("✅ Impression tracked")
        }
    } catch {
        print("❌ Failed to track impression: \(error)")
    }
}
```

### Add Reaction (Like)

```swift
func addLike(activity: StreamActivity, userEmail: String) async {
    let url = URL(string: "\(apiBase)/reactions/add")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    let body: [String: Any] = [
        "user_id": userEmail,
        "activity_id": activity.id,  // ✅ Use UUID
        "kind": "like"
    ]

    request.httpBody = try? JSONSerialization.data(withJSONObject: body)

    do {
        let (data, response) = try await URLSession.shared.data(for: request)
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
            let result = try JSONDecoder().decode(ReactionResponse.self, from: data)
            print("✅ Like added: \(result.reaction?.id ?? "unknown")")
        }
    } catch {
        print("❌ Failed to add like: \(error)")
    }
}

struct ReactionResponse: Codable {
    let success: Bool
    let message: String?
    let reaction: ReactionData?
}

struct ReactionData: Codable {
    let id: String
    let kind: String
    let activityId: String
    let userId: String

    enum CodingKeys: String, CodingKey {
        case id, kind
        case activityId = "activity_id"
        case userId = "user_id"
    }
}
```

### Remove Reaction (Unlike)

```swift
func removeLike(reactionId: String) async {
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
```

### Check Like Status

```swift
func checkIfLiked(activity: StreamActivity, userEmail: String) async -> Bool {
    let sanitizedEmail = userEmail.replacingOccurrences(of: "@", with: "_at_")
                                  .replacingOccurrences(of: ".", with: "_")

    let url = URL(string: "\(apiBase)/reactions/user/\(sanitizedEmail)/activity/\(activity.id)?kind=like")!

    do {
        let (data, _) = try await URLSession.shared.data(from: url)
        let result = try JSONDecoder().decode(ReactionCheckResponse.self, from: data)
        return result.hasReacted
    } catch {
        print("❌ Failed to check like status: \(error)")
        return false
    }
}

struct ReactionCheckResponse: Codable {
    let success: Bool
    let hasReacted: Bool
    let reaction: ReactionData?

    enum CodingKeys: String, CodingKey {
        case success
        case hasReacted = "has_reacted"
        case reaction
    }
}
```

## ❌ Common Mistakes

### 1. Using foreign_id Instead of id

```swift
// ❌ WRONG
let body = [
    "activity_id": activity.foreignId  // "goal:2025020829_576"
]

// ✅ CORRECT
let body = [
    "activity_id": activity.id  // "b227dc00-fb1f-11f0-8080-8001429e601f"
]
```

**Error you'll see:**
```
"activity_id must be a valid UUID version 1"
```

### 2. Missing activity.id in Model

```swift
// ❌ WRONG - Model missing id field
struct StreamActivity: Codable {
    let foreignId: String  // Only has foreign_id
}

// ✅ CORRECT - Model has both
struct StreamActivity: Codable {
    let id: String          // GetStream UUID
    let foreignId: String   // Custom ID
}
```

### 3. Worrying About Email Characters

```swift
// ❌ NO LONGER NEEDED - Backend handles this
let sanitizedEmail = email.replacingOccurrences(of: "@", with: "_at_")

// ✅ JUST SEND THE EMAIL - Backend sanitizes automatically
let body = ["user_id": "ntrienens@nhl.com"]
```

## 🔍 Debugging

### Get Complete API Guide

```bash
GET /api/v1/api-guide
```

Returns comprehensive documentation with examples.

### Get Reaction-Specific Help

```bash
GET /api/v1/reactions/help
```

Returns guidance on reaction requirements.

### Debug Request Format

```bash
POST /api/v1/analytics/debug
{
  "any": "data",
  "you": "want"
}
```

Echoes back what the server received.

## 🎯 Checklist for iOS Developers

- [ ] `StreamActivity` model includes `id: String` field
- [ ] Using `activity.id` for all API calls, not `activity.foreign_id`
- [ ] Decoding `id` from API response with correct CodingKey
- [ ] Impression tracking sends `activity.id`
- [ ] Reaction add/remove uses `activity.id`
- [ ] Added `ownReactions` and `reactionCounts` to model
- [ ] Using personalized feed endpoint to get reaction state
- [ ] Handling reaction responses correctly

## 📚 Additional Resources

- **Complete Guide**: `GET /api/v1/api-guide`
- **Reaction Help**: `GET /api/v1/reactions/help`
- **Personalization Guide**: `backend/PERSONALIZATION.md`
- **API Documentation**: `https://your-backend.com/docs` (Swagger UI)

## 🆘 Still Having Issues?

1. Check the error response - it includes helpful guidance
2. Visit `GET /api/v1/api-guide` for complete documentation
3. Use `POST /api/v1/analytics/debug` to see what the server receives
4. Verify your `StreamActivity` model includes the `id` field
5. Confirm you're using `activity.id`, not `activity.foreign_id`

## ✅ Summary

**For ALL endpoints:**
- ✅ Use `activity.id` (GetStream UUID)
- ✅ Emails work in `user_id` (auto-sanitized)
- ✅ Both `snake_case` and `camelCase` accepted
- ❌ Never use `activity.foreign_id` for reactions

**Key Changes Needed in iOS App:**
1. Ensure `StreamActivity` model has `id: String` field
2. Use `activity.id` for all impression and reaction calls
3. That's it! Backend handles the rest.
