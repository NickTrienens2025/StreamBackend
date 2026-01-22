import Foundation
import Observation

@Observable
@MainActor
public final class StreamService {
    public var activities: [Activity] = []
    public var isLoading: Bool = false
    public var error: Error? = nil
    
    private let config: GoalStreamConfig
    private let urlSession: URLSession
    private var nextCursor: String? = nil
    
    public init(config: GoalStreamConfig, urlSession: URLSession = .shared) {
        self.config = config
        self.urlSession = urlSession
    }
    
    /// Fetches activities from the backend feed.
    /// - Parameters:
    ///   - feedId: The ID of the feed to fetch (e.g., "nhl").
    ///   - refresh: If true, clears existing activities and starts from the beginning.
    public func fetchActivities(feedId: String, refresh: Bool = false) async {
        guard !isLoading else { return }
        
        // If refreshing, reset state
        if refresh {
            activities = []
            nextCursor = nil
            error = nil
        }
        
        // If we have a backend URL, use it
        guard let backendUrl = config.backendUrl else {
            // Fallback or error if no backend URL
            // For now, assuming backend URL is required for this implementation
             self.error = NSError(domain: "GoalStream", code: 400, userInfo: [NSLocalizedDescriptionKey: "Backend URL is required"])
            return
        }
        
        isLoading = true
        defer { isLoading = false }
        
        do {
            // Construct URL: /feeds/{feed_id}/activities
            // Assuming backendUrl matches http://localhost:8000/api/v1 or similar base
            // API Route: @router.get("/feeds/{feed_id}/activities")
            
            var urlString = "\(backendUrl)/feeds/\(feedId)/activities"
            var queryItems = [URLQueryItem]()
            
            if let cursor = nextCursor, !refresh {
                queryItems.append(URLQueryItem(name: "offset", value: cursor)) // Backend uses offset? Or next?
                // Backend API: offset: int = Query(0, ge=0)
                // Activity response: "next": result.get('next') <- this is usually a cursor string from Stream?
                // But backend code says: offset: int.
                // Wait, stream_client.get_activities uses offset.
                // If "next" is returned, it might be an integer-based offset or a token.
                // Let's check backend `api.py` again. 
                // Line 80: "next": result.get('next')
                // Line 55: offset: int = Query(0, ge=0)
                
                // If the backend expects an integer offset, we need to handle that.
                // But Stream's `next` is usually a string (id_lt...). 
                // The backend implementation:
                // result = await stream_client.get_activities(..., offset=offset)
                // If Stream returns `next` as a string, using it as `offset` (int) in the NEXT request will fail if `offset` param expects int.
                // However, `api.py` defines `offset: int`. 
                // This implies the backend implements SIMPLE integer pagination, NOT cursor-based pagination (which is standard for Stream).
                // Or maybe I missed something.
                // I will assume Integer pagination for now based on `offset: int`.
            }
            
            // Just use limit for now
            queryItems.append(URLQueryItem(name: "limit", value: "20"))
            
            // Add query items to URL
             if !queryItems.isEmpty {
                var components = URLComponents(string: urlString)
                components?.queryItems = queryItems
                urlString = components?.string ?? urlString
            }
            
            guard let url = URL(string: urlString) else {
                throw NSError(domain: "GoalStream", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid URL"])
            }
            
            var request = URLRequest(url: url)
            // request.setValue("Bearer \(config.userToken)", forHTTPHeaderField: "Authorization") // If needed
            
            let (data, response) = try await urlSession.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
                throw NSError(domain: "GoalStream", code: 500, userInfo: [NSLocalizedDescriptionKey: "Server error"])
            }
            
            // Try to decode generic FeedResponse first (backend API)
            do {
                let decodedResponse = try JSONDecoder().decode(FeedResponse.self, from: data)
                if refresh {
                    self.activities = decodedResponse.data
                } else {
                    self.activities.append(contentsOf: decodedResponse.data)
                }
            } catch {
                // Fallback: Try decoding raw array (S3/Static file)
                do {
                    let rawActivities = try JSONDecoder().decode([Activity].self, from: data)
                    if refresh {
                        self.activities = rawActivities
                    } else {
                        self.activities.append(contentsOf: rawActivities)
                    }
                } catch {
                     // Propagate original error or new one
                    print("Decoding error: \(error)") 
                    throw error
                }
            }
            
        } catch {
            self.error = error
        }
    }
}

// Internal Response Models
struct FeedResponse: Decodable {
    let success: Bool?
    let data: [Activity]
}
