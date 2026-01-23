#!/bin/bash

# Configuration
SERVICE_ID="srv-d5o5a4khg0os73fctdt0"
RENDER_CLI="/opt/homebrew/bin/render"

echo "🔍 Checking deployment status for Service ID: $SERVICE_ID"

# Get the latest deploy
LATEST_DEPLOY_JSON=$($RENDER_CLI deploys list $SERVICE_ID --output json | head -n 30) # Grab enough lines to likely cover the first object

# Extract ID and Status (using grep/sed as jq might not be available, keeping it portable)
DEPLOY_ID=$(echo "$LATEST_DEPLOY_JSON" | grep -m 1 '"id":' | cut -d '"' -f 4)
STATUS=$(echo "$LATEST_DEPLOY_JSON" | grep -m 1 '"status":' | cut -d '"' -f 4)
COMMIT=$(echo "$LATEST_DEPLOY_JSON" | grep -m 1 '"message":' | cut -d '"' -f 4)

echo "📌 Latest Deploy ID: $DEPLOY_ID"
echo "📝 Commit Message: $COMMIT"
echo "🚦 Current Status: $STATUS"

if [ "$STATUS" == "live" ]; then
    echo "✅ Application is LIVE!"
    exit 0
elif [ "$STATUS" == "build_in_progress" ] || [ "$STATUS" == "update_in_progress" ]; then
    echo "⏳ Deployment in progress..."
    exit 0
elif [ "$STATUS" == "build_failed" ] || [ "$STATUS" == "update_failed" ]; then
    echo "❌ Deployment FAILED."
    exit 1
else
    echo "ℹ️  Status: $STATUS"
fi
