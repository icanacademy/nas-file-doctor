#!/usr/bin/env python3
"""
Fix NAS File Doctor - Complete Solution
"""
import os
import sys
import subprocess
import time
import shutil

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def step1_stop_app():
    """Stop running app"""
    print("Step 1: Stopping existing app...")
    subprocess.run(["pkill", "-f", "python.*app.py"], stderr=subprocess.DEVNULL)
    time.sleep(2)
    print("  ✓ App stopped")

def step2_clean_indexes():
    """Clean all index directories"""
    print("\nStep 2: Cleaning index directories...")
    for index_dir in ["file_index", "app/file_index"]:
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir, ignore_errors=True)
            print(f"  ✓ Removed {index_dir}")

def step3_test_ftp():
    """Test FTP connection"""
    print("\nStep 3: Testing FTP connection...")
    import ftplib
    
    try:
        ftp = ftplib.FTP()
        ftp.encoding = 'utf-8'
        ftp.connect('192.168.68.142', 21)
        ftp.login('admin', 'ican1441!!')
        ftp.set_pasv(True)
        
        # Test root
        items = []
        ftp.retrlines('LIST', items.append)
        print(f"  ✓ FTP connected - found {len(items)} items in root")
        
        # Test HDD2
        ftp.cwd('/HDD2')
        items = []
        ftp.retrlines('LIST', items.append)
        print(f"  ✓ Found {len(items)} items in /HDD2")
        
        ftp.quit()
        return True
        
    except Exception as e:
        print(f"  ✗ FTP test failed: {e}")
        return False

def step4_fix_app():
    """Fix the app code to handle missing index"""
    print("\nStep 4: Patching app code...")
    
    # Read current app.py
    app_file = "app/app.py"
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if "def init_app():" in content:
        print("  ✓ App already patched")
        return
    
    # Add initialization function
    patch = '''
def init_app():
    """Initialize app on startup"""
    global file_indexer
    
    # Ensure index directory exists
    index_dir = "file_index"
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
        logger.info(f"Created index directory: {index_dir}")
    
    # Re-initialize indexer to ensure clean state
    file_indexer = FileIndexer(index_dir)
    logger.info("Initialized file indexer")
    
    # Initialize NAS connection
    if init_nas_connection():
        logger.info("NAS connection initialized")
        # Don't auto-index on startup to prevent crashes
        # Users can manually trigger indexing
    else:
        logger.warning("Failed to initialize NAS connection")

'''
    
    # Find where to insert the patch (after imports, before init_nas_connection)
    insert_pos = content.find("def init_nas_connection():")
    if insert_pos > 0:
        content = content[:insert_pos] + patch + content[insert_pos:]
        
        # Also update the main section to call init_app
        main_section = "if __name__ == '__main__':"
        main_pos = content.find(main_section)
        if main_pos > 0:
            # Replace the startup code
            old_startup = "if init_nas_connection():"
            new_startup = "init_app()"
            content = content.replace(old_startup, new_startup)
        
        # Write patched file
        with open(app_file, 'w') as f:
            f.write(content)
        
        print("  ✓ App patched successfully")
    else:
        print("  ✗ Could not patch app")

def step5_start_app():
    """Start the app"""
    print("\nStep 5: Starting app...")
    
    # Change to app directory
    os.chdir("/Users/icanacademy/nas-file-doctor")
    
    # Start app
    proc = subprocess.Popen([sys.executable, "app/app.py"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    
    print("  Waiting for app to start...")
    time.sleep(5)
    
    # Test if running
    import requests
    try:
        resp = requests.get("http://localhost:5001/api/status", timeout=5)
        if resp.status_code == 200:
            print("  ✓ App started successfully")
            return proc
        else:
            print(f"  ✗ App returned status {resp.status_code}")
    except:
        print("  ✗ App failed to start")
    
    # Show last few lines of output
    print("\nApp output:")
    try:
        output = proc.stdout.read(1000).decode('utf-8', errors='ignore')
        print(output)
    except:
        pass
    
    return None

def step6_trigger_index():
    """Trigger index rebuild"""
    print("\nStep 6: Triggering index rebuild...")
    
    import requests
    try:
        resp = requests.post("http://localhost:5001/api/index/update", timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            print("  ✓ Indexing started")
            print(f"    Files: {result.get('indexed_files', 'in progress')}")
            print(f"    Errors: {result.get('errors', 0)}")
            print(f"    Duration: {result.get('duration', 'in progress')}s")
        else:
            print(f"  ✗ Index trigger failed: {resp.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

if __name__ == "__main__":
    print("NAS File Doctor - Complete Fix")
    print("=" * 50)
    
    # Run all steps
    step1_stop_app()
    step2_clean_indexes()
    
    if not step3_test_ftp():
        print("\n✗ Cannot proceed without FTP connection")
        print("Please check:")
        print("  1. NAS is powered on")
        print("  2. Network connection is active")
        print("  3. FTP service is enabled on NAS")
        sys.exit(1)
    
    step4_fix_app()
    proc = step5_start_app()
    
    if proc:
        step6_trigger_index()
        
        print("\n" + "=" * 50)
        print("✓ Fix complete!")
        print("=" * 50)
        print("\nThe app is now running at: http://localhost:5001")
        print("\nIMPORTANT: The indexing will take several minutes.")
        print("Monitor progress at: http://localhost:5001/api/index/stats")
        print("\nTo stop: pkill -f 'python.*app.py'")
    else:
        print("\n✗ Fix failed - check the output above for errors")