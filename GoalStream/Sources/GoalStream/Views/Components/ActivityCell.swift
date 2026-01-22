import SwiftUI
import BrightcovePlayerSDK

public struct ActivityCell: View {
    let activity: Activity
    let config: GoalStreamConfig
    
    @State private var video: BCOVVideo? = nil
    
    public init(activity: Activity, config: GoalStreamConfig) {
        self.activity = activity
        self.config = config
    }
    
    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header: Player info and Game context
            HStack(alignment: .center, spacing: 12) {
                if let headshot = activity.scoringPlayerHeadshot, let url = URL(string: headshot) {
                    AsyncImage(url: url) { image in
                        image.resizable()
                             .aspectRatio(contentMode: .fill)
                             .clipShape(Circle())
                    } placeholder: {
                        Circle().fill(Color.gray.opacity(0.3))
                    }
                    .frame(width: 48, height: 48)
                    .overlay(Circle().stroke(Color.white, lineWidth: 1))
                    .shadow(radius: 2)
                }
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(activity.scoringPlayerName ?? "Unknown Player")
                        .font(.headline)
                        .foregroundColor(.primary)
                    
                    HStack(spacing: 6) {
                        Text(activity.scoringTeam ?? "")
                            .font(.caption)
                            .bold()
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.black.opacity(0.8)) // Team color placeholder
                            .foregroundColor(.white)
                            .cornerRadius(4)
                        
                        Text("vs")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        
                        Text(activity.opponent ?? "")
                            .font(.caption)
                            .bold()
                            .foregroundColor(.secondary)
                    }
                }
                
                Spacer()
                
                // Score Badge
                VStack(alignment: .trailing, spacing: 2) {
                    Text("GOAL")
                        .font(.caption)
                        .fontWeight(.black)
                        .foregroundColor(.red)
                    
                    if let home = activity.homeScore, let away = activity.awayScore, let homeTeam = activity.homeTeam, let awayTeam = activity.awayTeam {
                        Text("\(homeTeam) \(home) - \(away) \(awayTeam)")
                            .font(.caption2)
                            .fontWeight(.medium)
                            .foregroundColor(.secondary)
                    } else if let period = activity.period {
                        Text("P\(period)")
                             .font(.caption2)
                             .foregroundColor(.secondary)
                    }
                }
            }
            .padding(.horizontal)
            
            // Video Player
            // We use the extracted ID to decide if we show the player placeholder/loader
            // But checking 'video' state tells us if it's ready.
            // Ideally we check if an ID Exists first.
            if let videoId = extractVideoId(from: activity) {
                ZStack {
                    // Pass the cached video object if available, OR the ID for fallback
                    BrightcoveVideoView(
                        policyKey: config.brightcovePolicyKey,
                        accountId: config.brightcoveAccountId,
                        videoId: videoId,
                        video: video,
                        autoPlay: true
                    )
                    .aspectRatio(16/9, contentMode: .fit)
                    .background(Color.black)
                    .cornerRadius(12)
                    .clipped()
                }
            } else {
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .aspectRatio(16/9, contentMode: .fit)
                    .overlay(Text("No Video Available").font(.caption))
                    .cornerRadius(12)
            }
            
            // Action Bar (Likes/Comments would go here)
            HStack {
                Button(action: {}) {
                    Image(systemName: "heart")
                }
                Text("\(activity.reactionCounts?["like"] ?? 0)")
                    .font(.caption)
                
                Spacer()
                
                if let tags = activity.interestTags {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack {
                            ForEach(tags.prefix(3), id: \.self) { tag in
                                Text("#\(tag.split(separator: ":").last ?? "")")
                                    .font(.caption2)
                                    .foregroundColor(.blue)
                            }
                        }
                    }
                }
                
                HStack(spacing: 4) {
                    Image(systemName: "clock")
                    if #available(iOS 15.0, *) {
                        Text(activity.time.formatted(date: .omitted, time: .shortened))
                    } else {
                        Text("Recently")
                    }
                }
                .font(.caption2)
                .foregroundColor(.gray)
            }
            .padding(.horizontal)
            .padding(.bottom, 8)
        }
        .background(Color(UIColor.secondarySystemBackground)) // Card background
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.1), radius: 5, x: 0, y: 2)
        .task {
            // Load video metadata on appear
            if let videoId = extractVideoId(from: activity) {
                self.video = await VideoMetadataService.shared.fetchVideo(
                    with: videoId,
                    accountID: config.brightcoveAccountId,
                    policyKey: config.brightcovePolicyKey
                )
            }
        }
    }
    
    private func extractVideoId(from activity: Activity) -> String? {
        // Priority 1: Highlight Clip Default (Int64)
        if let clip = activity.highlightClipDefault {
            return String(clip)
        }
        // Priority 2: Discrete Clip Default (Int64)
        if let clip = activity.discreteClipDefault {
            return String(clip)
        }
        
        // Priority 3: foreign_id: "goal:2025020749_143" -> strip "goal:"?
        // Note: The user prompt says "these fields tie to brightcove Id's".
        // The foreign_id might just be an activity ID, not a video ID.
        // But previously I assumed it was. I'll keep it as a fallback but low priority.
        if let fid = activity.foreignId, fid.starts(with: "goal:") {
             return String(fid.dropFirst(5))
        }
        if activity.object.starts(with: "goal:") {
             return String(activity.object.dropFirst(5))
        }
        
        return nil
    }
}
