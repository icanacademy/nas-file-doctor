from flask import Flask, render_template_string, request, jsonify, send_file, Response
import os
import ftplib
import io
import mimetypes
from datetime import datetime

app = Flask(__name__)

# NAS Configuration
NAS_IP = '192.168.68.142'
NAS_USERNAME = 'admin'
NAS_PASSWORD = 'ican1441!!'
FTP_PORT = 21

class SimpleFTP:
    def __init__(self):
        self.conn = None
        
    def connect(self):
        try:
            self.conn = ftplib.FTP()
            self.conn.encoding = 'utf-8'
            self.conn.connect(NAS_IP, FTP_PORT)
            self.conn.login(NAS_USERNAME, NAS_PASSWORD)
            self.conn.set_pasv(True)
            return True
        except Exception as e:
            print(f"FTP connection failed: {e}")
            return False
            
    def list_files(self, path="/HDD2"):
        files = []
        try:
            self.conn.cwd(path)
            items = []
            self.conn.retrlines('LIST', items.append)
            
            for item in items:
                parts = item.split(None, 8)
                if len(parts) >= 9:
                    name = parts[8]
                    is_dir = parts[0].startswith('d')
                    if name not in ['.', '..']:
                        files.append({
                            'name': name,
                            'path': f"{path}/{name}".replace('//', '/'),
                            'is_directory': is_dir,
                            'size': int(parts[4]) if not is_dir else 0
                        })
        except Exception as e:
            print(f"Error listing files: {e}")
            
        return files
        
    def download_file(self, file_path):
        try:
            data = []
            self.conn.retrbinary(f'RETR {file_path}', data.append)
            return b''.join(data)
        except Exception as e:
            print(f"Download error: {e}")
            return None

ftp = SimpleFTP()

@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Simple NAS File Access</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h1>Simple NAS File Access</h1>
        <div class="row">
            <div class="col-md-8">
                <button class="btn btn-primary" onclick="loadFiles()">Load Files</button>
                <div id="files" class="mt-3"></div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadFiles(path = '/HDD2') {
            const response = await fetch(`/api/files?path=${encodeURIComponent(path)}`);
            const files = await response.json();
            
            let html = `<h3>Files in: ${path}</h3>`;
            
            if (path !== '/HDD2') {
                const parentPath = path.substring(0, path.lastIndexOf('/')) || '/HDD2';
                html += `<button class="btn btn-secondary mb-3" onclick="loadFiles('${parentPath}')">← Back</button><br>`;
            }
            
            files.forEach(file => {
                if (file.is_directory) {
                    html += `
                        <div class="card mb-2 bg-light">
                            <div class="card-body">
                                <h5>📁 ${file.name}</h5>
                                <button class="btn btn-primary" onclick="loadFiles('${file.path}')">Open Folder</button>
                            </div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="card mb-2">
                            <div class="card-body">
                                <h5>📄 ${file.name}</h5>
                                <p>Size: ${file.size} bytes</p>
                                <button class="btn btn-success" onclick="downloadFile('${file.path}')">Download</button>
                            </div>
                        </div>
                    `;
                }
            });
            
            document.getElementById('files').innerHTML = html;
        }
        
        function downloadFile(path) {
            window.open(`/api/download?path=${encodeURIComponent(path)}`, '_blank');
        }
    </script>
</body>
</html>
    ''')

@app.route('/api/files')
def api_files():
    path = request.args.get('path', '/HDD2')
    if not ftp.connect():
        return jsonify([])
    
    files = ftp.list_files(path)
    return jsonify(files)

@app.route('/api/download')
def api_download():
    file_path = request.args.get('path')
    if not file_path:
        return "No file path provided", 400
        
    if not ftp.connect():
        return "FTP connection failed", 500
        
    file_data = ftp.download_file(file_path)
    if not file_data:
        return "Download failed", 404
        
    filename = os.path.basename(file_path)
    mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
    return send_file(
        io.BytesIO(file_data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)