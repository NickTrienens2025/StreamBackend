// swift-tools-version: 6.2
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "GoalStream",
    platforms: [
        .iOS(.v17)
    ],
    products: [
        // Products define the executables and libraries a package produces, making them visible to other packages.
        .library(
            name: "GoalStream",
            targets: ["GoalStream"]
        ),
    ],
    dependencies: [
        .package(url: "https://github.com/brightcove/brightcove-player-sdk-ios.git", from: "6.13.3")
    ],
    targets: [
        // Targets are the basic building blocks of a package, defining a module or a test suite.
        // Targets can depend on other targets in this package and products from dependencies.
        .target(
            name: "GoalStream",
            dependencies: [
                .product(name: "BrightcovePlayerSDK", package: "brightcove-player-sdk-ios")
            ]
        ),
        .testTarget(
            name: "GoalStreamTests",
            dependencies: ["GoalStream"]
        ),
    ]
)
