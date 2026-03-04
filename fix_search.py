#!/usr/bin/env python3
"""
Fix search issues in NAS File Doctor
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from nas_connector import NASConnector
from file_indexer import FileIndexer
import shutil
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    """Test NAS connection"""
    print("Testing NAS connection...")
    
    nas_ip = os.getenv('NAS_IP', '192.168.68.142')
    nas_username = os.getenv('NAS_USERNAME', 'admin')
    nas_password = os.getenv('NAS_PASSWORD', 'ican1441!!')
    
    nas = NASConnector(nas_ip, nas_username, nas_password)
    
    # Try FTP connection
    if nas.connect_ftp(21, passive=True, encoding='UTF-8'):
        print("✓ FTP connection successful")
        
        # Test listing files
        try:
            files = nas.list_files_ftp("/")
            print(f"✓ Found {len(files)} items in root directory")
            for f in files[:5]:
                print(f"  - {f['name']}")
                
            # Try HDD2
            files = nas.list_files_ftp("/HDD2")
            print(f"✓ Found {len(files)} items in /HDD2")
            for f in files[:5]:
                print(f"  - {f['name']}")
                
        except Exception as e:
            print(f"✗ Error listing files: {e}")
            
        return nas
    else:
        print("✗ FTP connection failed")
        return None

def rebuild_index():
    """Rebuild the search index from scratch"""
    print("\nRebuilding search index...")
    
    # Clear old index
    index_dir = "file_index"
    if os.path.exists(index_dir):
        print("Removing old index...")
        shutil.rmtree(index_dir, ignore_errors=True)
    
    # Create new indexer
    indexer = FileIndexer(index_dir)
    print("✓ Created new index")
    
    # Connect to NAS
    nas = test_connection()
    if not nas:
        print("✗ Cannot rebuild index without NAS connection")
        return
    
    # Start indexing
    print("\nStarting index rebuild...")
    print("This may take several minutes...")
    
    result = indexer.index_files(nas, start_path="/HDD2", max_depth=10)
    
    print(f"\n✓ Index rebuild complete!")
    print(f"  - Indexed files: {result['indexed_files']}")
    print(f"  - Errors: {result['errors']}")
    print(f"  - Duration: {result['duration']} seconds")
    
    # Test search
    print("\nTesting search functionality...")
    test_queries = ["mp4", "jpg", "pdf", "movie", "photo"]
    
    for query in test_queries:
        results = indexer.search(query, limit=5)
        print(f"\nSearch '{query}': {len(results)} results")
        for r in results[:2]:
            print(f"  - {r['filename']}")

def test_search_only():
    """Test search without rebuilding"""
    print("Testing current search index...")
    
    indexer = FileIndexer("file_index")
    stats = indexer.get_stats()
    
    print(f"Current index stats:")
    print(f"  - Total files: {stats['total_files']}")
    print(f"  - Index size: {stats['index_size'] / 1024 / 1024:.2f} MB")
    print(f"  - Last update: {stats['last_update']}")
    
    # Test various search patterns
    test_queries = [
        ("test", None),
        ("*.mp4", None),
        ("movie", "video"),
        ("document", "document"),
        ("2024", None),
    ]
    
    for query, file_type in test_queries:
        results = indexer.search(query, file_type, limit=5)
        print(f"\nSearch '{query}' (type: {file_type}): {len(results)} results")
        for r in results[:3]:
            print(f"  - {r['filename']} ({r['path']})")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix NAS File Doctor search")
    parser.add_argument('--test-only', action='store_true', help='Only test search, don\'t rebuild')
    parser.add_argument('--rebuild', action='store_true', help='Force rebuild index')
    
    args = parser.parse_args()
    
    if args.test_only:
        test_search_only()
    elif args.rebuild:
        rebuild_index()
    else:
        # Default: test then ask
        test_search_only()
        response = input("\nWould you like to rebuild the index? (y/n): ")
        if response.lower() == 'y':
            rebuild_index()