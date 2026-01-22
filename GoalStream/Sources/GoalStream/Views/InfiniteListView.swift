import SwiftUI

public struct InfiniteListView: View {
    @State private var streamService: StreamService
    @State private var selectedFilter: String? = nil
    @State private var selectedTeams: Set<String> = []
    
    let config: GoalStreamConfig
    
    // Hardcoded filters for now, or could be passed in
    let availableFilters = ["All", "Goal", "Save", "Hit", "Fight"] 
    
    public init(config: GoalStreamConfig) {
        self.config = config
        self._streamService = State(initialValue: StreamService(config: config))
    }
    
    public var body: some View {
        VStack(spacing: 0) {
            // Filter Bar
            VStack(spacing: 0) {
                FilterView(tags: availableFilters, selectedTag: $selectedFilter)
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
        .onChange(of: selectedFilter) { _, _ in }
        .onChange(of: selectedTeams) { _, _ in }
    }
    
    private func shouldShow(_ activity: Activity) -> Bool {
        // 1. Filter by Event Type
        if let filter = selectedFilter, filter != "All" {
            // Simple mapping: check verb or tags
            if filter == "Goal" { 
                if activity.verb != "score" { return false }
            } else if let tags = activity.interestTags {
                if !tags.contains(where: { $0.localizedCaseInsensitiveContains(filter) }) {
                   return false 
                }
            }
        }
        
        // 2. Filter by Teams (if any selected)
        if !selectedTeams.isEmpty {
            // We need to check if this activity is related to any selected team.
            // Checks: scoringTeam, homeTeam, awayTeam, or interestTags.
            var matchFound = false
            
            for team in selectedTeams {
                // Check direct fields (assuming simplified or full name match)
                if let scoring = activity.scoringTeam, scoring.localizedCaseInsensitiveContains(team) { matchFound = true; break }
                if let home = activity.homeTeam, home.localizedCaseInsensitiveContains(team) { matchFound = true; break }
                if let away = activity.awayTeam, away.localizedCaseInsensitiveContains(team) { matchFound = true; break }
                
                // Check Interest Tags (e.g. "team:DET" vs "Detroit Red Wings")
                // This is fuzzy. ideally we map "Detroit Red Wings" -> "DET" or check if tag contains part of name..
                // For now, let's assume loose string matching might work if backend sends full names in tags,
                // OR we rely on the direct fields above which are more likely to support this.
                if let tags = activity.interestTags {
                   if tags.contains(where: { $0.localizedCaseInsensitiveContains(team) }) { matchFound = true; break }
                }
            }
            
            if !matchFound { return false }
        }
        
        return true
    }
}
