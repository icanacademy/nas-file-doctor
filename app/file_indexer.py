import os
import json
import time
from datetime import datetime
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, DATETIME, BOOLEAN
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.writing import AsyncWriter
import logging
from typing import List, Dict, Optional
from nas_connector import NASConnector

logger = logging.getLogger(__name__)

class FileIndexer:
    def __init__(self, index_dir: str = "file_index"):
        self.index_dir = index_dir
        self.schema = Schema(
            path=ID(stored=True, unique=True),
            filename=TEXT(stored=True),
            content=TEXT(stored=False),
            size=NUMERIC(stored=True),
            modified=DATETIME(stored=True),
            file_type=TEXT(stored=True),
            is_directory=BOOLEAN(stored=True),
            parent_dir=TEXT(stored=True)
        )
        
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
            self.ix = index.create_in(index_dir, self.schema)
        else:
            self.ix = index.open_dir(index_dir)
            
        self.last_index_time = None
        
    def index_files(self, nas_connector: NASConnector, share_name: str = None, 
                   start_path: str = "/", max_depth: int = 20) -> Dict:
        """Index all files from NAS"""
        start_time = time.time()
        indexed_count = 0
        error_count = 0
        
        writer = self.ix.writer()
        
        def index_recursive(path: str, depth: int = 0):
            nonlocal indexed_count, error_count
            
            if depth > max_depth:
                return
                
            try:
                if nas_connector.connection_type == "SMB":
                    files = nas_connector.list_files_smb(share_name, path)
                else:
                    files = nas_connector.list_files_ftp(path)
                    
                for file in files:
                    try:
                        writer.update_document(
                            path=file['path'],
                            filename=file['name'],
                            size=file.get('size', 0),
                            modified=file.get('modified', datetime.now()),
                            file_type=file.get('type', 'file'),
                            is_directory=file['is_directory'],
                            parent_dir=os.path.dirname(file['path'])
                        )
                        indexed_count += 1
                        
                        if file['is_directory']:
                            index_recursive(file['path'], depth + 1)
                            
                    except Exception as e:
                        logger.error(f"Error indexing file {file['name']}: {str(e)}")
                        error_count += 1
                        
            except Exception as e:
                logger.error(f"Error accessing path {path}: {str(e)}")
                error_count += 1
                
        index_recursive(start_path)
        writer.commit()
        
        self.last_index_time = datetime.now()
        duration = time.time() - start_time
        
        return {
            'indexed_files': indexed_count,
            'errors': error_count,
            'duration': round(duration, 2),
            'last_update': self.last_index_time.isoformat()
        }
        
    def search(self, query: str, file_type: Optional[str] = None, 
               limit: int = 100) -> List[Dict]:
        """Search indexed files"""
        results = []
        
        with self.ix.searcher() as searcher:
            parser = MultifieldParser(["filename", "path"], schema=self.schema)
            
            try:
                # Try wildcard search for partial matches
                search_query = f"*{query}*"
                if file_type:
                    search_query = f"{search_query} AND file_type:{file_type}"
                    
                q = parser.parse(search_query)
                search_results = searcher.search(q, limit=limit)
                
                for hit in search_results:
                    results.append({
                        'path': hit['path'],
                        'filename': hit['filename'],
                        'size': hit.get('size', 0),
                        'modified': hit.get('modified').isoformat() if hit.get('modified') else None,
                        'file_type': hit.get('file_type', 'file'),
                        'is_directory': hit.get('is_directory', False),
                        'score': hit.score
                    })
                    
            except Exception as e:
                logger.error(f"Search error: {str(e)}")
                
        return results
        
    def get_stats(self) -> Dict:
        """Get index statistics"""
        with self.ix.searcher() as searcher:
            return {
                'total_files': searcher.doc_count(),
                'last_update': self.last_index_time.isoformat() if self.last_index_time else None,
                'index_size': sum(os.path.getsize(os.path.join(self.index_dir, f)) 
                                for f in os.listdir(self.index_dir))
            }
            
    def clear_index(self):
        """Clear the entire index"""
        try:
            writer = self.ix.writer()
            writer.commit(optimize=True)
            # Re-create the index
            self.ix = index.create_in(self.index_dir, self.schema)
            self.last_index_time = None
            logger.info("Index cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing index: {str(e)}")
            # Just create a new index if clearing fails
            import shutil
            shutil.rmtree(self.index_dir, ignore_errors=True)
            os.makedirs(self.index_dir, exist_ok=True)
            self.ix = index.create_in(self.index_dir, self.schema)
            self.last_index_time = None