import Foundation

/// Configuration for the GoalStream library.
public struct GoalStreamConfig: Sendable {
    /// Stream API Key
    public let streamApiKey: String
    /// Stream User Token
    public let userToken: String
    /// Brightcove Account ID
    public let brightcoveAccountId: String
    /// Brightcove Policy Key
    public let brightcovePolicyKey: String
    /// Base URL for the backend proxy (optional, if using proxy endpoints)
    public let backendUrl: String?

    public init(
        streamApiKey: String,
        userToken: String,
        brightcoveAccountId: String,
        brightcovePolicyKey: String,
        backendUrl: String? = nil
    ) {
        self.streamApiKey = streamApiKey
        self.userToken = userToken
        self.brightcoveAccountId = brightcoveAccountId
        self.brightcovePolicyKey = brightcovePolicyKey
        self.backendUrl = backendUrl
    }
}
