import Foundation
import BrightcovePlayerSDK

@MainActor
public class VideoMetadataService: ObservableObject {
    public static let shared = VideoMetadataService()
    
    // Cache for BCOVVideo objects
    private let videoCache = NSCache<NSString, BCOVVideo>()
    
    // In-flight requests to prevent duplicate fetches
    private var activeTasks: [String: Task<BCOVVideo?, Error>] = [:]
    
    private init() {
        videoCache.countLimit = 100 // Keep last 100 videos in memory
    }
    
    public func fetchVideo(with videoID: String, accountID: String, policyKey: String) async -> BCOVVideo? {
        // 1. Check Cache
        if let cachedVideo = videoCache.object(forKey: videoID as NSString) {
            return cachedVideo
        }
        
        // 2. Check Deduplication
        if let existingTask = activeTasks[videoID] {
            return try? await existingTask.value
        }
        
        // 3. Fetch from Network
        let task = Task<BCOVVideo?, Error> {
            return try await withCheckedThrowingContinuation { continuation in
                let playbackService = BCOVPlaybackService(accountId: accountID, policyKey: policyKey)
                playbackService?.findVideo(withVideoID: videoID, parameters: nil) { (video: BCOVVideo?, json: [AnyHashable : Any]?, error: Error?) in
                    if let video = video {
                        continuation.resume(returning: video)
                    } else if let error = error {
                        continuation.resume(throwing: error)
                    } else {
                        continuation.resume(returning: nil)
                    }
                }
            }
        }
        
        activeTasks[videoID] = task
        
        do {
            let video = try await task.value
            if let video = video {
                videoCache.setObject(video, forKey: videoID as NSString)
            }
            activeTasks[videoID] = nil
            return video
        } catch {
            print("Error fetching video \(videoID): \(error.localizedDescription)")
            activeTasks[videoID] = nil
            return nil
        }
    }
}
