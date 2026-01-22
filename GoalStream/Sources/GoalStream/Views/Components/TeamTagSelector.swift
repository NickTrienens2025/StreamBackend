import SwiftUI

public struct TeamTagSelector: View {
    @Binding var selectedTeams: Set<String>
    @State private var searchText = ""
    @State private var isSearching = false
    
    // Hardcoded NHL teams for now - can be moved to a service or config
    let allTeams = [
        "Anaheim Ducks", "Boston Bruins", "Buffalo Sabres", "Calgary Flames", 
        "Carolina Hurricanes", "Chicago Blackhawks", "Colorado Avalanche", 
        "Columbus Blue Jackets", "Dallas Stars", "Detroit Red Wings", 
        "Edmonton Oilers", "Florida Panthers", "Los Angeles Kings", 
        "Minnesota Wild", "Montreal Canadiens", "Nashville Predators", 
        "New Jersey Devils", "New York Islanders", "New York Rangers", 
        "Ottawa Senators", "Philadelphia Flyers", "Pittsburgh Penguins", 
        "San Jose Sharks", "Seattle Kraken", "St. Louis Blues", 
        "Tampa Bay Lightning", "Toronto Maple Leafs", "Utah Hockey Club",
        "Vancouver Canucks", "Vegas Golden Knights", "Washington Capitals", 
        "Winnipeg Jets"
    ]
    
    var filteredTeams: [String] {
        if searchText.isEmpty {
            return allTeams
        } else {
            return allTeams.filter { $0.localizedCaseInsensitiveContains(searchText) }
        }
    }
    
    public init(selectedTeams: Binding<Set<String>>) {
        self._selectedTeams = selectedTeams
    }
    
    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Selected Tags Area
            if !selectedTeams.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(Array(selectedTeams).sorted(), id: \.self) { team in
                            TeamTag(team: team) {
                                withAnimation {
                                    selectedTeams.remove(team)
                                }
                            }
                        }
                    }
                    .padding(.horizontal)
                }
            }
            
            // Search Input
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                TextField("Add Team...", text: $searchText)
                    .textFieldStyle(PlainTextFieldStyle())
                    .onTapGesture {
                        withAnimation {
                            isSearching = true
                        }
                    }
                
                if !searchText.isEmpty {
                    Button(action: {
                        withAnimation {
                            searchText = ""
                        }
                    }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .padding(12)
            .background(Color(.secondarySystemBackground))
            .cornerRadius(12)
            .padding(.horizontal)
            
            // Autocomplete List
            if isSearching || !searchText.isEmpty {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 0) {
                        ForEach(filteredTeams, id: \.self) { team in
                            if !selectedTeams.contains(team) {
                                Button(action: {
                                    withAnimation {
                                        selectedTeams.insert(team)
                                        searchText = ""
                                        // Optional: dismiss search? Keep it for adding more?
                                    }
                                }) {
                                    HStack {
                                        // Placeholder for Logo
                                        Circle()
                                            .fill(Color.gray.opacity(0.2))
                                            .frame(width: 24, height: 24)
                                            .overlay(Text(team.prefix(1)).font(.caption).foregroundColor(.gray))
                                        
                                        Text(team)
                                            .foregroundColor(.primary)
                                            .font(.body)
                                        Spacer()
                                        Image(systemName: "plus.circle.fill")
                                            .foregroundColor(.blue)
                                            .font(.title3)
                                    }
                                    .padding(.vertical, 12)
                                    .padding(.horizontal)
                                    .contentShape(Rectangle()) // Make full row tappable
                                }
                                Divider()
                                    .padding(.leading, 50) // Indent divider
                            }
                        }
                    }
                }
                .frame(maxHeight: 250) // Limit height
                .background(Color(UIColor.systemBackground))
                .cornerRadius(12)
                .shadow(color: Color.black.opacity(0.1), radius: 5, x: 0, y: 2)
                .padding(.horizontal)
                .transition(.opacity)
            }
        }
        .animation(.easeInOut, value: isSearching)
        .animation(.easeInOut, value: searchText)
        .animation(.easeInOut, value: selectedTeams)
    }
}

struct TeamTag: View {
    let team: String
    let onDelete: () -> Void
    
    var body: some View {
        HStack(spacing: 6) {
            Text(team)
                .font(.subheadline)
                .fontWeight(.medium)
            
            Button(action: onDelete) {
                Image(systemName: "xmark")
                    .font(.system(size: 10, weight: .bold))
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.blue.opacity(0.1))
        .foregroundColor(.blue)
        .clipShape(Capsule())
        .overlay(
            Capsule()
                .stroke(Color.blue.opacity(0.3), lineWidth: 1)
        )
    }
}
