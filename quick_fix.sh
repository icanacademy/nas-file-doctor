#!/bin/bash

echo "Quick fix for NAS File Doctor search"
echo "===================================="

# Stop the app if running
echo "1. Stopping any running instances..."
pkill -f "python.*app.py" 2>/dev/null
sleep 2

# Clear the corrupted index
echo "2. Clearing corrupted index..."
rm -rf file_index app/file_index 2>/dev/null

# Start the app
echo "3. Starting the app..."
cd /Users/icanacademy/nas-file-doctor
python3 app/app.py &
APP_PID=$!

echo "4. Waiting for app to start..."
sleep 5

# Check if app is running
if curl -s http://localhost:5001/api/status > /dev/null; then
    echo "✓ App is running"
    
    # Trigger index update
    echo "5. Triggering index rebuild..."
    curl -X POST http://localhost:5001/api/index/update
    
    echo -e "\n\n✓ Fix complete!"
    echo "The app is now running in the background (PID: $APP_PID)"
    echo "Access it at: http://localhost:5001"
    echo ""
    echo "Note: The initial indexing may take several minutes."
    echo "You can check progress at: http://localhost:5001/api/index/stats"
else
    echo "✗ App failed to start. Check the logs."
fi