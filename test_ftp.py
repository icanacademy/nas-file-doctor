#!/usr/bin/env python3
import ftplib
import os

# Test basic FTP connectivity
NAS_IP = '192.168.68.142'
NAS_USERNAME = 'admin'
NAS_PASSWORD = 'ican1441!!'

print(f"Testing FTP connection to {NAS_IP}...")

try:
    ftp = ftplib.FTP()
    ftp.encoding = 'utf-8'
    ftp.connect(NAS_IP, 21, timeout=30)
    print("✓ Connected to FTP server")
    
    ftp.login(NAS_USERNAME, NAS_PASSWORD)
    print("✓ Login successful")
    
    ftp.set_pasv(True)
    print("✓ Passive mode enabled")
    
    # List root directory
    print("\nListing root directory:")
    root_items = []
    ftp.retrlines('LIST', root_items.append)
    
    print(f"Found {len(root_items)} items:")
    for item in root_items[:10]:
        print(f"  {item}")
    
    # Try to access HDD2
    print("\nTrying to access /HDD2...")
    try:
        ftp.cwd('/HDD2')
        print("✓ Changed to /HDD2")
        
        hdd2_items = []
        ftp.retrlines('LIST', hdd2_items.append)
        print(f"Found {len(hdd2_items)} items in /HDD2:")
        for item in hdd2_items[:10]:
            print(f"  {item}")
            
    except Exception as e:
        print(f"✗ Error accessing /HDD2: {e}")
    
    ftp.quit()
    print("\n✓ FTP test successful!")
    
except Exception as e:
    print(f"\n✗ FTP test failed: {e}")
    print("\nPossible solutions:")
    print("1. Check if NAS is powered on and connected to network")
    print("2. Verify IP address is correct (current: 192.168.68.142)")
    print("3. Check FTP service is enabled on the NAS")
    print("4. Verify username/password are correct")