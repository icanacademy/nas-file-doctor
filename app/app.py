from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
import os
import io
import logging
from datetime import datetime
from functools import wraps
import mimetypes
from dotenv import load_dotenv
from nas_connector import NASConnector
from file_indexer import FileIndexer
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nas_connector = None
file_indexer = FileIndexer()
scheduler = BackgroundScheduler()

NAS_IP = os.getenv('NAS_IP', '192.168.1.100')
NAS_USERNAME = os.getenv('NAS_USERNAME', 'admin')
NAS_PASSWORD = os.getenv('NAS_PASSWORD', 'admin')
SMB_SHARE_NAME = os.getenv('SMB_SHARE_NAME', 'Public')
SMB_PORT = int(os.getenv('SMB_PORT', '445'))
FTP_PORT = int(os.getenv('FTP_PORT', '21'))
INDEX_UPDATE_INTERVAL = int(os.getenv('INDEX_UPDATE_INTERVAL', '3600'))
MAX_DOWNLOAD_SIZE = int(os.getenv('MAX_DOWNLOAD_SIZE', '1073741824'))

def init_nas_connection():
    """Initialize NAS connection"""
    global nas_connector
    
    nas_connector = NASConnector(NAS_IP, NAS_USERNAME, NAS_PASSWORD)
    
    # Try FTP first since we know the FTP configuration works
    if nas_connector.connect_ftp(FTP_PORT, passive=True, encoding='UTF-8'):
        logger.info("Successfully connected to NAS via FTP")
    elif nas_connector.connect_smb(SMB_SHARE_NAME, SMB_PORT):
        logger.info("Successfully connected to NAS via SMB")
    else:
        logger.error("Failed to connect to NAS")
        return False
        
    return True

def update_index():
    """Update file index"""
    if nas_connector:
        logger.info("Starting scheduled index update...")
        # For FTP, we might need to navigate to HDD2 first
        start_path = "/HDD2" if nas_connector.connection_type == "FTP" else "/"
        result = file_indexer.index_files(nas_connector, SMB_SHARE_NAME, start_path)
        logger.info(f"Index update completed: {result}")

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search():
    """Search files"""
    query = request.args.get('q', '')
    file_type = request.args.get('type', None)
    limit = int(request.args.get('limit', 100))
    
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
        
    results = file_indexer.search(query, file_type, limit)
    
    return jsonify({
        'query': query,
        'results': results,
        'count': len(results)
    })

@app.route('/api/browse', methods=['GET'])
def browse():
    """Browse directory"""
    path = request.args.get('path', '/')
    
    if not nas_connector:
        return jsonify({'error': 'NAS not connected'}), 503
        
    try:
        if nas_connector.connection_type == "SMB":
            files = nas_connector.list_files_smb(SMB_SHARE_NAME, path)
        else:
            files = nas_connector.list_files_ftp(path)
            
        return jsonify({
            'path': path,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<path:file_path>')
def download(file_path):
    """Download file using multiple methods"""
    try:
        file_path = '/' + file_path
        filename = os.path.basename(file_path)
        
        # Method 1: Try FTP download first
        logger.info(f"Attempting FTP download: {file_path}")
        if nas_connector and nas_connector.connection_type == "FTP":
            file_data = nas_connector.download_file_ftp(file_path)
            if file_data and len(file_data) > 1000:  # Reasonable file size
                logger.info(f"FTP download successful: {len(file_data)} bytes")
                return send_file(
                    io.BytesIO(file_data),
                    mimetype=mimetypes.guess_type(filename)[0] or 'application/octet-stream',
                    as_attachment=True,
                    download_name=filename
                )
        
        # Method 2: Try HTTP proxy download
        logger.info(f"FTP failed, trying HTTP download: {file_path}")
        import requests
        import urllib.parse
        
        try:
            # Create a session and try to get the file
            session = requests.Session()
            
            # Set headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }
            
            # Try different URL patterns for iptime NAS
            possible_urls = [
                f"http://192.168.68.142/download{file_path}",
                f"http://192.168.68.142/files{file_path}",
                f"http://192.168.68.142/nas{file_path}",
                f"http://192.168.68.142{file_path}"
            ]
            
            for url in possible_urls:
                try:
                    logger.info(f"Trying HTTP download: {url}")
                    response = session.get(url, headers=headers, timeout=30, stream=True)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', 'application/octet-stream')
                        
                        # Check if it's actually a file (not HTML error page)
                        if not content_type.startswith('text/html'):
                            logger.info(f"Successfully downloading from: {url}")
                            
                            def generate():
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        yield chunk
                            
                            return Response(
                                generate(),
                                headers={
                                    'Content-Disposition': f'attachment; filename="{filename}"',
                                    'Content-Type': content_type
                                }
                            )
                            
                except Exception as e:
                    logger.warning(f"URL {url} failed: {str(e)}")
                    continue
            
            # If all HTTP methods fail, return error with helpful message
            return jsonify({
                'error': 'Could not download file via HTTP',
                'message': 'File access requires manual navigation',
                'instructions': {
                    'step1': 'Open Finder (Mac) or File Explorer (Windows)',
                    'step2': 'Go to: smb://192.168.68.142/HDD2',
                    'step3': 'Login with: admin / ican1441!!', 
                    'step4': f'Navigate to: {file_path}',
                    'step5': 'Download the file directly'
                }
            }), 404
            
        except Exception as e:
            logger.error(f"HTTP download error: {str(e)}")
            return jsonify({'error': f'Download failed: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def download_via_http(file_path):
    """Try to download file via HTTP from NAS web interface"""
    try:
        import requests
        import urllib.parse
        
        # First, try to login to get session
        session = requests.Session()
        
        # Login to NAS
        login_url = f"http://{NAS_IP}/login.cgi"
        login_data = {
            'username': NAS_USERNAME,
            'password': NAS_PASSWORD
        }
        
        logger.info(f"Attempting HTTP login to NAS")
        login_response = session.post(login_url, data=login_data, timeout=10)
        
        if login_response.status_code == 200:
            logger.info("HTTP login successful, attempting file download")
            
            # Try different URL patterns that iptime NAS might use
            possible_urls = [
                f"http://{NAS_IP}/download{file_path}",
                f"http://{NAS_IP}/files{file_path}",
                f"http://{NAS_IP}/shared{file_path}",
                f"http://{NAS_IP}/nas{file_path}",
                f"http://{NAS_IP}{file_path}"
            ]
            
            for url in possible_urls:
                try:
                    logger.info(f"Trying HTTP download URL: {url}")
                    response = session.get(url, timeout=30)
                    
                    if response.status_code == 200 and len(response.content) > 0:
                        logger.info(f"HTTP download successful from: {url}")
                        return response.content
                        
                except Exception as e:
                    logger.warning(f"HTTP URL {url} failed: {str(e)}")
                    continue
                    
        logger.error("All HTTP download methods failed")
        return None
        
    except Exception as e:
        logger.error(f"HTTP download error: {str(e)}")
        return None

@app.route('/api/preview/<path:file_path>')
def preview(file_path):
    """Preview file - Disabled due to FTP encoding issues"""
    return jsonify({
        'error': 'Preview disabled due to FTP encoding issues',
        'message': 'Use the "Locate" button to get file access instructions',
        'file_path': '/' + file_path if not file_path.startswith('/') else file_path
    }), 404

@app.route('/api/index/update', methods=['POST'])
def update_index_manual():
    """Manually trigger index update"""
    if not nas_connector:
        return jsonify({'error': 'NAS not connected'}), 503
        
    try:
        result = file_indexer.index_files(nas_connector, SMB_SHARE_NAME)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/index/stats', methods=['GET'])
def index_stats():
    """Get index statistics"""
    stats = file_indexer.get_stats()
    stats['nas_connected'] = nas_connector is not None
    stats['connection_type'] = nas_connector.connection_type if nas_connector else None
    return jsonify(stats)

@app.route('/api/status', methods=['GET'])
def status():
    """System status"""
    return jsonify({
        'nas_connected': nas_connector is not None,
        'connection_type': nas_connector.connection_type if nas_connector else None,
        'nas_ip': NAS_IP,
        'index_stats': file_indexer.get_stats()
    })

@app.route('/api/debug/list-root', methods=['GET'])
def debug_list_root():
    """Debug: List root directory to find available folders"""
    if not nas_connector:
        return jsonify({'error': 'NAS not connected'}), 503
        
    try:
        if nas_connector.connection_type == "SMB":
            files = nas_connector.list_files_smb(SMB_SHARE_NAME, "/")
        else:
            files = nas_connector.list_files_ftp("/")
            
        return jsonify({
            'connection_type': nas_connector.connection_type,
            'root_files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/sample-files', methods=['GET'])
def debug_sample_files():
    """Debug: Show sample of indexed files"""
    try:
        with file_indexer.ix.searcher() as searcher:
            # Get first 20 files from index
            results = []
            for doc in searcher.documents():
                results.append({
                    'filename': doc.get('filename', 'unknown'),
                    'path': doc.get('path', 'unknown'),
                    'file_type': doc.get('file_type', 'unknown'),
                    'size': doc.get('size', 0)
                })
                if len(results) >= 20:
                    break
                    
        return jsonify({
            'sample_files': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/check-file/<path:file_path>', methods=['GET'])
def debug_check_file(file_path):
    """Debug: Check if a specific file can be accessed"""
    if not nas_connector:
        return jsonify({'error': 'NAS not connected'}), 503
        
    try:
        if not file_path.startswith('/'):
            file_path = '/' + file_path
            
        parent_dir = os.path.dirname(file_path)
        target_filename = os.path.basename(file_path)
        
        # List directory contents
        if nas_connector.connection_type == "SMB":
            dir_files = nas_connector.list_files_smb(SMB_SHARE_NAME, parent_dir)
        else:
            dir_files = nas_connector.list_files_ftp(parent_dir)
            
        # Find exact match
        exact_match = None
        for f in dir_files:
            if f['name'] == target_filename:
                exact_match = f
                break
                
        # Find similar matches
        similar_matches = [f for f in dir_files if target_filename.lower() in f['name'].lower()]
        
        return jsonify({
            'target_file': target_filename,
            'parent_directory': parent_dir,
            'exact_match_found': exact_match is not None,
            'exact_match': exact_match,
            'similar_matches': similar_matches,
            'all_files_in_directory': [f['name'] for f in dir_files]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/ftp-test', methods=['GET'])
def debug_ftp_test():
    """Debug: Test basic FTP functionality"""
    if not nas_connector or nas_connector.connection_type != "FTP":
        return jsonify({'error': 'FTP not connected'}), 503
        
    try:
        results = {}
        
        # Test 1: FTP status
        try:
            results['ftp_status'] = nas_connector.ftp_conn.getwelcome()
            results['current_dir'] = nas_connector.ftp_conn.pwd()
        except Exception as e:
            results['ftp_error'] = str(e)
        
        # Test 2: List root directory
        try:
            root_files = nas_connector.list_files_ftp('/')
            results['root_listing'] = {
                'success': True,
                'file_count': len(root_files),
                'files': [f['name'] for f in root_files[:10]]  # First 10 files
            }
        except Exception as e:
            results['root_listing'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 3: Try to access HDD2
        try:
            hdd2_files = nas_connector.list_files_ftp('/HDD2')
            results['hdd2_listing'] = {
                'success': True,
                'file_count': len(hdd2_files),
                'files': [f['name'] for f in hdd2_files[:10]]
            }
        except Exception as e:
            results['hdd2_listing'] = {
                'success': False,
                'error': str(e)
            }
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if init_nas_connection():
        # Skip automatic indexing on startup to prevent crashes
        pass
        
    app.run(
        host=os.getenv('APP_HOST', '0.0.0.0'),
        port=int(os.getenv('APP_PORT', '5001')),
        debug=False  # Disable debug mode
    )