#!/usr/bin/env python3
"""
Rebuild search index and start NAS File Doctor
"""
import os
import sys
import subprocess
import shutil
import time

def kill_existing_processes():
    """Kill any existing app processes"""
    print("Stopping existing processes...")
    subprocess.run(["pkill", "-f", "python.*app.py"], stderr=subprocess.DEVNULL)
    time.sleep(2)

def clean_index():
    """Remove corrupted index files"""
    print("Cleaning corrupted index...")
    for index_dir in ["file_index", "app/file_index"]:
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir, ignore_errors=True)
            print(f"  ✓ Removed {index_dir}")

def start_app_and_rebuild():
    """Start the app and trigger index rebuild"""
    print("\nStarting NAS File Doctor...")
    
    # Change to app directory
    os.chdir("/Users/icanacademy/nas-file-doctor")
    
    # Start the app in background
    proc = subprocess.Popen([sys.executable, "app/app.py"], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
    
    print("Waiting for app to initialize...")
    time.sleep(5)
    
    # Check if app is running
    try:
        import requests
        
        # Check status
        resp = requests.get("http://localhost:5001/api/status")
        if resp.status_code == 200:
            print("✓ App is running successfully")
            status = resp.json()
            print(f"  - NAS Connected: {status['nas_connected']}")
            print(f"  - Connection Type: {status['connection_type']}")
            
            # Trigger index rebuild
            print("\nTriggering index rebuild...")
            resp = requests.post("http://localhost:5001/api/index/update")
            
            if resp.status_code == 200:
                result = resp.json()
                print("✓ Index rebuild started")
                print(f"  - Files indexed: {result.get('indexed_files', 'in progress')}")
                print(f"  - Duration: {result.get('duration', 'in progress')} seconds")
            else:
                print(f"✗ Index rebuild failed: {resp.text}")
                
        else:
            print("✗ App failed to start properly")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        
    print(f"\n{'='*50}")
    print("NAS File Doctor is now running!")
    print(f"{'='*50}")
    print("Access the web interface at: http://localhost:5001")
    print("\nNote: The indexing process will run in the background.")
    print("It may take several minutes to index all files.")
    print("\nTo check indexing progress:")
    print("  curl http://localhost:5001/api/index/stats | python3 -m json.tool")
    print("\nTo stop the app:")
    print("  pkill -f 'python.*app.py'")
    
    return proc

if __name__ == "__main__":
    print("NAS File Doctor - Search Fix Utility")
    print("="*40)
    
    # Step 1: Kill existing processes
    kill_existing_processes()
    
    # Step 2: Clean corrupted index
    clean_index()
    
    # Step 3: Start app and rebuild index
    proc = start_app_and_rebuild()
    
    print("\nPress Ctrl+C to stop the app")
    
    try:
        # Keep the script running
        proc.wait()
    except KeyboardInterrupt:
        print("\nStopping app...")
        proc.terminate()
        print("✓ App stopped")