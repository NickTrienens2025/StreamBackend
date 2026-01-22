import SwiftUI

public struct InfiniteListView: View {
    @State private var streamService: StreamService
    @State private var selectedFilters: Set<String> = []
    @State private var selectedTeams: Set<String> = []
    
    let config: GoalStreamConfig
    
    // Hardcoded filters for now, or could be passed in
    let availableFilters = ["Goal", "Save", "Hit", "Fight"] 
    
    public init(config: GoalStreamConfig) {
        self.config = config
        self._streamService = State(initialValue: StreamService(config: config))
    }
    
    public var body: some View {
        VStack(spacing: 0) {
            // Filter Bar
            VStack(spacing: 0) {
                FilterView(tags: availableFilters, selectedTags: $selectedFilters)
                    .padding(.vertical, 8)
                
                // Team Tag Selector
                TeamTagSelector(selectedTeams: $selectedTeams)
                    .padding(.bottom, 8)
            }
            .background(Color(UIColor.systemBackground))
            .shadow(color: Color.black.opacity(0.05), radius: 2, x: 0, y: 2)
            .zIndex(1)
            
            // Feed
            ScrollView {
                LazyVStack(spacing: 16) {
                    ForEach(streamService.activities) { activity in
                        if shouldShow(activity) {
                            ActivityCell(activity: activity, config: config)
                                .padding(.horizontal)
                                .onAppear {
                                    if activity.id == streamService.activities.last?.id {
                                        Task {
                                            await streamService.fetchActivities(feedId: "nhl")
                                        }
                                    }
                                }
                        }
                    }
                    
                    if streamService.isLoading {
                        ProgressView()
                        .padding()
                        .frame(maxWidth: .infinity)
                    }
                }
                .padding(.vertical)
            }
            .refreshable {
                await streamService.fetchActivities(feedId: "nhl", refresh: true)
            }
        }
        .task {
            // Initial load
            if streamService.activities.isEmpty {
                await streamService.fetchActivities(feedId: "nhl")
            }
        }
        .onChange(of: selectedFilters) { _, _ in }
        .onChange(of: selectedTeams) { _, _ in }
    }
    
    private func shouldShow(_ activity: Activity) -> Bool {
        // 1. Filter by Event Type (OR Logic)
        // If no filters are selected, we show EVERYTHING (acts as "All")
        // If filters are selected, the activity must match AT LEAST ONE of them.
        
        let eventMatch: Bool
        if selectedFilters.isEmpty {
            eventMatch = true
        } else {
            // Check if activity matches ANY of the selected filters
            eventMatch = selectedFilters.contains { filter in
                if filter == "Goal" {
                    return activity.verb == "score"
                } else if let tags = activity.interestTags {
                    return tags.contains(where: { $0.localizedCaseInsensitiveContains(filter) })
                }
                return false
            }
        }
        
        if !eventMatch { return false }
        
        // 2. Filter by Teams (OR Logic) - if any selected
        if !selectedTeams.isEmpty {
            // We need to check if this activity is related to ANY selected team.
            var matchFound = false
            
            // Optimization: check if we can find any intersection between selected teams and activity teams
            for team in selectedTeams {
                // Check direct fields
                if let scoring = activity.scoringTeam, scoring.localizedCaseInsensitiveContains(team) { matchFound = true; break }
                if let home = activity.homeTeam, home.localizedCaseInsensitiveContains(team) { matchFound = true; break }
                if let away = activity.awayTeam, away.localizedCaseInsensitiveContains(team) { matchFound = true; break }
                
                // Check Interest Tags
                if let tags = activity.interestTags {
                   if tags.contains(where: { $0.localizedCaseInsensitiveContains(team) }) { matchFound = true; break }
                }
            }
            
            if !matchFound { return false }
        }
        
        return true
    }
}
