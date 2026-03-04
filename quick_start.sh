#!/bin/bash

echo "Quick Start - NAS File Doctor"
echo "============================="

# Kill existing
pkill -f "python.*app.py" 2>/dev/null
sleep 2

# Clean and create index directory
rm -rf file_index app/file_index 2>/dev/null
mkdir -p file_index

# Create empty index
cd /Users/icanacademy/nas-file-doctor
python3 -c "
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, DATETIME, BOOLEAN
import os

schema = Schema(
    path=ID(stored=True, unique=True),
    filename=TEXT(stored=True),
    content=TEXT(stored=False),
    size=NUMERIC(stored=True),
    modified=DATETIME(stored=True),
    file_type=TEXT(stored=True),
    is_directory=BOOLEAN(stored=True),
    parent_dir=TEXT(stored=True)
)

if not os.path.exists('file_index'):
    os.makedirs('file_index')
    
ix = index.create_in('file_index', schema)
print('✓ Created empty search index')
"

# Start app
echo "Starting app..."
python3 app/app.py &
APP_PID=$!

sleep 5

# Test
if curl -s http://localhost:5001/api/status > /dev/null 2>&1; then
    echo "✓ App is running (PID: $APP_PID)"
    echo ""
    echo "Access at: http://localhost:5001"
    echo ""
    echo "To rebuild search index:"
    echo "  1. Open http://localhost:5001"
    echo "  2. Click 'Update Index' button"
    echo ""
    echo "To stop: pkill -f 'python.*app.py'"
else
    echo "✗ App failed to start"
fi