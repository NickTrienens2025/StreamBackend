import Foundation

/// Represents a Stream Activity.
public struct Activity: Identifiable, Codable, Sendable {
    // Standard Stream fields
    public let id: String?
    public let actor: String
    public let verb: String
    public let object: String
    public let target: String?
    public let time: Date
    public let interestTags: [String]?
    public let filterTags: [String]?
    public let reactionCounts: [String: Int]?
    public let latestReactions: [String: [Reaction]]?
    
    // Custom Goal Data
    public let foreignId: String?
    public let scoringPlayerId: String?
    public let scoringPlayerName: String?
    public let scoringPlayerHeadshot: String?
    public let scoringPlayerPosition: String?
    public let scoringPlayerSweater: Int?
    public let scoringTeam: String?
    public let opponent: String?
    public let homeTeam: String?
    public let awayTeam: String?
    public let isHomeGoal: Bool?
    public let shotType: String?
    public let goalType: String?
    public let gameId: String?
    public let period: Int?
    public let homeScore: Int?
    public let awayScore: Int?
    
    // New Fields from JSON Source
    public let primaryAssistId: String?
    public let primaryAssistName: String?
    public let secondaryAssistId: String?
    public let secondaryAssistName: String?
    public let assistsCount: Int?
    public let goalForTeam: String?
    public let goalAgainstTeam: String?
    public let highlightClipDefault: Int64?
    public let highlightClipFr: Int64?
    public let discreteClipDefault: Int64?
    public let discreteClipFr: Int64?
    public let shotXCoord: Double?
    public let shotYCoord: Double?
    public let shotZone: String?
    public let goalieId: String?
    public let goalieTeam: String?
    public let strength: String?
    public let isGameWinner: Bool?
    public let isOvertime: Bool?
    public let isShootout: Bool?
    public let isEmptyNet: Bool?
    public let isPenaltyShot: Bool?
    public let isPowerPlay: Bool?
    public let isShortHanded: Bool?
    public let isTyingGoal: Bool?
    public let isGoAheadGoal: Bool?
    public let score: Int? // "score": 10
    
    // Custom mapping for backend snake_case to swift camelCase
    enum CodingKeys: String, CodingKey {
        case id
        case actor
        case verb
        case object
        case target
        case time
        case interestTags = "interest_tags"
        case filterTags = "filter_tags"
        case reactionCounts = "reaction_counts"
        case latestReactions = "latest_reactions"
        
        case foreignId = "foreign_id"
        case scoringPlayerId = "scoring_player_id"
        case scoringPlayerName = "scoring_player_name"
        case scoringPlayerHeadshot = "scoring_player_headshot"
        case scoringPlayerPosition = "scoring_player_position"
        case scoringPlayerSweater = "scoring_player_sweater"
        case scoringTeam = "scoring_team"
        case opponent
        case homeTeam = "home_team"
        case awayTeam = "away_team"
        case isHomeGoal = "is_home_goal"
        case shotType = "shot_type"
        case goalType = "goal_type"
        case gameId = "game_id"
        case period
        case homeScore = "home_score"
        case awayScore = "away_score"
        
        // New Keys
        case primaryAssistId = "primary_assist_id"
        case primaryAssistName = "primary_assist_name"
        case secondaryAssistId = "secondary_assist_id"
        case secondaryAssistName = "secondary_assist_name"
        case assistsCount = "assists_count"
        case goalForTeam = "goal_for_team"
        case goalAgainstTeam = "goal_against_team"
        case highlightClipDefault = "highlight_clip_default"
        case highlightClipFr = "highlight_clip_fr"
        case discreteClipDefault = "discrete_clip_default"
        case discreteClipFr = "discrete_clip_fr"
        case shotXCoord = "shot_x_coord"
        case shotYCoord = "shot_y_coord"
        case shotZone = "shot_zone"
        case goalieId = "goalie_id"
        case goalieTeam = "goalie_team"
        case strength
        case isGameWinner = "is_game_winner"
        case isOvertime = "is_overtime"
        case isShootout = "is_shootout"
        case isEmptyNet = "is_empty_net"
        case isPenaltyShot = "is_penalty_shot"
        case isPowerPlay = "is_power_play"
        case isShortHanded = "is_short_handed"
        case isTyingGoal = "is_tying_goal"
        case isGoAheadGoal = "is_go_ahead_goal"
        case score
    }
    
    public init(
        id: String? = nil,
        actor: String,
        verb: String,
        object: String,
        target: String? = nil,
        time: Date,
        interestTags: [String]? = nil,
        filterTags: [String]? = nil,
        reactionCounts: [String: Int]? = nil,
        latestReactions: [String: [Reaction]]? = nil,
        foreignId: String? = nil,
        scoringPlayerId: String? = nil,
        scoringPlayerName: String? = nil,
        scoringPlayerHeadshot: String? = nil,
        scoringTeam: String? = nil,
        opponent: String? = nil,
        gameId: String? = nil
    ) {
        self.id = id
        self.actor = actor
        self.verb = verb
        self.object = object
        self.target = target
        self.time = time
        self.interestTags = interestTags
        self.filterTags = filterTags
        self.reactionCounts = reactionCounts
        self.latestReactions = latestReactions
        self.foreignId = foreignId
        self.scoringPlayerId = scoringPlayerId
        self.scoringPlayerName = scoringPlayerName
        self.scoringPlayerHeadshot = scoringPlayerHeadshot
        self.scoringTeam = scoringTeam
        self.opponent = opponent
        self.gameId = gameId
        
        // Init others to nil for now in manual init
        self.scoringPlayerPosition = nil
        self.scoringPlayerSweater = nil
        self.homeTeam = nil
        self.awayTeam = nil
        self.isHomeGoal = nil
        self.shotType = nil
        self.goalType = nil
        self.period = nil
        self.homeScore = nil
        self.awayScore = nil
        
        self.primaryAssistId = nil
        self.primaryAssistName = nil
        self.secondaryAssistId = nil
        self.secondaryAssistName = nil
        self.assistsCount = nil
        self.goalForTeam = nil
        self.goalAgainstTeam = nil
        self.highlightClipDefault = nil
        self.highlightClipFr = nil
        self.discreteClipDefault = nil
        self.discreteClipFr = nil
        self.shotXCoord = nil
        self.shotYCoord = nil
        self.shotZone = nil
        self.goalieId = nil
        self.goalieTeam = nil
        self.strength = nil
        self.isGameWinner = nil
        self.isOvertime = nil
        self.isShootout = nil
        self.isEmptyNet = nil
        self.isPenaltyShot = nil
        self.isPowerPlay = nil
        self.isShortHanded = nil
        self.isTyingGoal = nil
        self.isGoAheadGoal = nil
        self.score = nil
    }
}

/// Represents a user interaction (Like, Comment, etc.)
public struct Reaction: Identifiable, Codable, Sendable {
    public let id: String
    public let kind: String
    public let activityId: String
    public let userId: String
    public let data: [String: String]? // Simplified for now, can be generic or specific
    public let createAt: Date?
    
    enum CodingKeys: String, CodingKey {
        case id
        case kind
        case activityId = "activity_id"
        case userId = "user_id"
        case data
        case createAt = "created_at"
    }
}
