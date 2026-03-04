import os
import ftplib
from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure
import socket
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class NASConnector:
    def __init__(self, nas_ip: str, username: str, password: str):
        self.nas_ip = nas_ip
        self.username = username
        self.password = password
        self.connection_type = None
        self.smb_conn = None
        self.ftp_conn = None
        
    def connect_smb(self, share_name: str = "Public", port: int = 445) -> bool:
        """Connect to NAS via SMB/CIFS"""
        try:
            self.smb_conn = SMBConnection(
                self.username, 
                self.password,
                socket.gethostname(),
                "NAS2dual",
                use_ntlm_v2=True
            )
            
            if port == 445:
                self.smb_conn.connect(self.nas_ip, port)
            else:
                self.smb_conn.connect(self.nas_ip, 139)
                
            self.connection_type = "SMB"
            logger.info(f"Connected to NAS via SMB on port {port}")
            return True
            
        except Exception as e:
            logger.error(f"SMB connection failed: {str(e)}")
            return False
            
    def connect_ftp(self, port: int = 21, passive: bool = True, encoding: str = 'UTF-8') -> bool:
        """Connect to NAS via FTP"""
        try:
            self.ftp_conn = ftplib.FTP()
            self.ftp_conn.encoding = encoding  # Set UTF-8 encoding
            self.ftp_conn.connect(self.nas_ip, port)
            self.ftp_conn.login(self.username, self.password)
            self.ftp_conn.set_pasv(passive)
            self.connection_type = "FTP"
            logger.info(f"Connected to NAS via FTP on port {port} with encoding {encoding}")
            return True
            
        except Exception as e:
            logger.error(f"FTP connection failed: {str(e)}")
            return False
            
    def list_files_smb(self, share_name: str, path: str = "/") -> List[Dict]:
        """List files via SMB"""
        files = []
        try:
            items = self.smb_conn.listPath(share_name, path)
            for item in items:
                if item.filename not in ['.', '..']:
                    files.append({
                        'name': item.filename,
                        'path': os.path.join(path, item.filename),
                        'size': item.file_size,
                        'modified': datetime.fromtimestamp(item.last_write_time),
                        'is_directory': item.isDirectory,
                        'type': 'directory' if item.isDirectory else self._get_file_type(item.filename)
                    })
        except Exception as e:
            logger.error(f"Error listing SMB files: {str(e)}")
            
        return files
        
    def list_files_ftp(self, path: str = "/") -> List[Dict]:
        """List files via FTP"""
        files = []
        try:
            self.ftp_conn.cwd(path)
            items = []
            self.ftp_conn.retrlines('LIST', items.append)
            
            for item in items:
                parts = item.split(None, 8)
                if len(parts) >= 9:
                    name = parts[8]
                    is_dir = parts[0].startswith('d')
                    
                    files.append({
                        'name': name,
                        'path': os.path.join(path, name),
                        'size': int(parts[4]) if not is_dir else 0,
                        'is_directory': is_dir,
                        'type': 'directory' if is_dir else self._get_file_type(name)
                    })
                    
        except Exception as e:
            logger.error(f"Error listing FTP files: {str(e)}")
            
        return files
        
    def search_files(self, query: str, share_name: str = None, path: str = "/") -> List[Dict]:
        """Search for files matching query"""
        results = []
        query_lower = query.lower()
        
        def search_recursive(current_path: str):
            if self.connection_type == "SMB":
                files = self.list_files_smb(share_name, current_path)
            else:
                files = self.list_files_ftp(current_path)
                
            for file in files:
                if query_lower in file['name'].lower():
                    results.append(file)
                    
                if file['is_directory'] and len(results) < 1000:
                    search_recursive(file['path'])
                    
        search_recursive(path)
        return results
        
    def download_file_smb(self, share_name: str, file_path: str) -> bytes:
        """Download file via SMB"""
        try:
            file_obj = self.smb_conn.retrieveFile(share_name, file_path)
            return file_obj.read()
        except Exception as e:
            logger.error(f"Error downloading SMB file: {str(e)}")
            return None
            
    def download_file_ftp(self, file_path: str) -> bytes:
        """Download file via FTP"""
        try:
            logger.info(f"Downloading FTP file: {file_path}")
            
            # Ensure we're in the right directory and file exists
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            logger.info(f"Changing to directory: {directory}")
            logger.info(f"Downloading file: {filename}")
            
            # Try different approaches
            data = []
            
            # Method 1: Direct path retrieval
            try:
                logger.info(f"Method 1: Direct RETR {file_path}")
                self.ftp_conn.voidcmd('TYPE I')  # Set binary mode explicitly
                self.ftp_conn.retrbinary(f'RETR {file_path}', data.append)
                result = b''.join(data)
                logger.info(f"Method 1 successful: {len(result)} bytes")
                return result
            except Exception as e1:
                logger.warning(f"Method 1 failed: {str(e1)}")
                data = []
            
            # Method 2: Change directory then download
            try:
                logger.info(f"Method 2: CWD + RETR")
                current_dir = self.ftp_conn.pwd()
                self.ftp_conn.cwd(directory)
                self.ftp_conn.voidcmd('TYPE I')  # Set binary mode
                self.ftp_conn.retrbinary(f'RETR {filename}', data.append)
                self.ftp_conn.cwd(current_dir)  # Return to original directory
                result = b''.join(data)
                logger.info(f"Method 2 successful: {len(result)} bytes")
                return result
            except Exception as e2:
                logger.warning(f"Method 2 failed: {str(e2)}")
                data = []
            
            # Method 3: Try with different encodings
            try:
                logger.info(f"Method 3: Encoding variations")
                for encoding_method in ['utf-8', 'euc-kr', 'cp949']:
                    try:
                        if encoding_method == 'utf-8':
                            encoded_path = file_path
                        else:
                            encoded_path = file_path.encode('utf-8').decode(encoding_method, errors='ignore')
                        
                        logger.info(f"Trying encoding {encoding_method}: {encoded_path}")
                        self.ftp_conn.voidcmd('TYPE I')
                        self.ftp_conn.retrbinary(f'RETR {encoded_path}', data.append)
                        result = b''.join(data)
                        logger.info(f"Method 3 ({encoding_method}) successful: {len(result)} bytes")
                        return result
                    except Exception as e3:
                        logger.warning(f"Encoding {encoding_method} failed: {str(e3)}")
                        data = []
                        continue
            except Exception as e3:
                logger.warning(f"Method 3 failed: {str(e3)}")
            
            logger.error(f"All download methods failed for: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Fatal error downloading FTP file {file_path}: {str(e)}")
            return None
            
    def _get_file_type(self, filename: str) -> str:
        """Determine file type from extension"""
        ext = os.path.splitext(filename)[1].lower()
        
        type_map = {
            '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image', '.bmp': 'image',
            '.mp4': 'video', '.avi': 'video', '.mkv': 'video', '.mov': 'video', '.wmv': 'video',
            '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio', '.aac': 'audio', '.ogg': 'audio',
            '.pdf': 'document', '.doc': 'document', '.docx': 'document', '.xls': 'document',
            '.xlsx': 'document', '.ppt': 'document', '.pptx': 'document', '.txt': 'document',
            '.zip': 'archive', '.rar': 'archive', '.7z': 'archive', '.tar': 'archive', '.gz': 'archive'
        }
        
        return type_map.get(ext, 'file')
        
    def close(self):
        """Close all connections"""
        if self.smb_conn:
            self.smb_conn.close()
        if self.ftp_conn:
            self.ftp_conn.quit()