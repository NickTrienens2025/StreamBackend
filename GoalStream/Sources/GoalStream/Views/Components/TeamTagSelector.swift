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
                                selectedTeams.remove(team)
                            }
                        }
                    }
                    .padding(.horizontal)
                }
            }
            
            // Search Input
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.gray)
                TextField("Add Team...", text: $searchText)
                    .textFieldStyle(PlainTextFieldStyle())
                    .onTapGesture {
                        isSearching = true
                    }
                
                if !searchText.isEmpty {
                    Button(action: {
                        searchText = ""
                    }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.gray)
                    }
                }
            }
            .padding(10)
            .background(Color(.systemGray6))
            .cornerRadius(10)
            .padding(.horizontal)
            
            // Autocomplete List
            if isSearching || !searchText.isEmpty {
                ScrollView {
                    LazyVStack(alignment: .leading) {
                        ForEach(filteredTeams, id: \.self) { team in
                            if !selectedTeams.contains(team) {
                                Button(action: {
                                    selectedTeams.insert(team)
                                    searchText = ""
                                    // Optional: dismiss search? Keep it for adding more?
                                }) {
                                    HStack {
                                        Text(team)
                                            .foregroundColor(.primary)
                                        Spacer()
                                        Image(systemName: "plus.circle")
                                            .foregroundColor(.blue)
                                    }
                                    .padding(.vertical, 8)
                                    .padding(.horizontal)
                                }
                                Divider()
                                    .padding(.leading)
                            }
                        }
                    }
                }
                .frame(maxHeight: 200) // Limit height
            }
        }
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
        .padding(.vertical, 6)
        .background(Color.blue.opacity(0.1))
        .foregroundColor(.blue)
        .clipShape(Capsule())
        .overlay(
            Capsule()
                .stroke(Color.blue.opacity(0.3), lineWidth: 1)
        )
    }
}
