#!/bin/bash
# NHL Goals Scraper - Cron Job Runner
# This script runs the NHL goals scraper and logs output

# Set script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Log file with timestamp
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/scraper_$(date +%Y%m%d_%H%M%S).log"

# Load environment variables
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Run the scraper
echo "Starting NHL Goals Scraper at $(date)" | tee -a "$LOG_FILE"
echo "===============================================" | tee -a "$LOG_FILE"

python3 -m app.nhl_scraper_cron 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "===============================================" | tee -a "$LOG_FILE"
echo "Scraper finished at $(date) with exit code: $EXIT_CODE" | tee -a "$LOG_FILE"

# Keep only last 30 log files
cd "$LOG_DIR"
ls -t scraper_*.log | tail -n +31 | xargs -r rm

exit $EXIT_CODE
