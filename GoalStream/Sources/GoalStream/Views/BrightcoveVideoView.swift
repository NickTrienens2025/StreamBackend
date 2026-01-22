import SwiftUI
import BrightcovePlayerSDK

public struct BrightcoveVideoView: UIViewRepresentable {
    let policyKey: String
    let accountId: String
    let videoId: String?
    let video: BCOVVideo?
    let autoPlay: Bool
    
    public init(policyKey: String, accountId: String, videoId: String? = nil, video: BCOVVideo? = nil, autoPlay: Bool = true) {
        self.policyKey = policyKey
        self.accountId = accountId
        self.videoId = videoId
        self.video = video
        self.autoPlay = autoPlay
    }
    
    public func makeUIView(context: Context) -> BCOVPUIPlayerView {
        // Create the playback controller
        let manager = BCOVPlayerSDKManager.shared()
        let playbackController = manager?.createPlaybackController()
        
        // Configure playback service
        // Only needed if we are fetching internally (legacy/fallback)
        let playbackService = BCOVPlaybackService(accountId: accountId, policyKey: policyKey)
        
        let options = BCOVPUIPlayerViewOptions()
        // options.presentingViewController = ... 
        
        let playerView = BCOVPUIPlayerView(playbackController: playbackController, options: options, controlsView: BCOVPUIBasicControlView.withVODLayout())!
        
        // Initial Load Strategy
        if let video = video {
            // Video provided directly (cached)
            playbackController?.setVideos([video] as NSFastEnumeration)
            if autoPlay { playbackController?.autoPlay = true; playbackController?.play() }
        } else if let videoId = videoId, !videoId.isEmpty {
             // Fallback: Fetch internally if no video object provided
             playbackService?.findVideo(withVideoID: videoId, parameters: nil) { (video: BCOVVideo?, json: [AnyHashable : Any]?, error: Error?) in
                if let video = video {
                    playbackController?.setVideos([video] as NSFastEnumeration)
                    if self.autoPlay { playbackController?.autoPlay = true; playbackController?.play() }
                }
            }
        }
        
        context.coordinator.playbackController = playbackController
        return playerView
    }
    
    public func updateUIView(_ uiView: BCOVPUIPlayerView, context: Context) {
        // If the 'video' property changes (e.g. from nil to loaded), we need to update the player
        if let video = video, let controller = context.coordinator.playbackController {
            // Check if we are already playing this video to avoid reset?
            // BCOVVideo doesn't have easy equality check, but we can check session
            // For now, simple set (might restart playback if view updates frequently)
            // To be safe, we might want to check context.coordinator.currentVideoId
             
            // Optimization: Only set if changed
            // Using object identity might work if it's the same instance from cache
             if context.coordinator.currentVideo != video {
                 controller.setVideos([video] as NSFastEnumeration)
                 if autoPlay { controller.autoPlay = true; controller.play() }
                 context.coordinator.currentVideo = video
             }
        }
    }
    
    public func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    public class Coordinator {
        var playbackController: BCOVPlaybackController?
        var currentVideo: BCOVVideo?
    }
}
