import SwiftUI

public struct FilterView: View {
    public let tags: [String]
    @Binding public var selectedTag: String?
    
    public init(tags: [String], selectedTag: Binding<String?>) {
        self.tags = tags
        self._selectedTag = selectedTag
    }
    
    public var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(tags, id: \.self) { tag in
                    FilterChip(
                        title: tag,
                        isSelected: selectedTag == tag,
                        action: {
                            if selectedTag == tag {
                                selectedTag = nil
                            } else {
                                selectedTag = tag
                            }
                        }
                    )
                }
            }
            .padding(.horizontal)
        }
    }
}

struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline)
                .fontWeight(.medium)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(isSelected ? Color.blue : Color.gray.opacity(0.2))
                .foregroundColor(isSelected ? .white : .primary)
                .clipShape(Capsule())
        }
    }
}
