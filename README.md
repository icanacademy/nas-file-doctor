# NAS File Doctor

A powerful local file search and management application for iptime NAS2dual devices. This web-based tool provides fast file searching, browsing, preview, and download capabilities.

## Features

- **Smart Search**: Full-text search with Whoosh indexing engine
- **File Browser**: Navigate through directories with breadcrumb navigation
- **File Preview**: Preview images and text files directly in browser
- **Download Manager**: Download files with size limits
- **Auto-indexing**: Scheduled index updates for new files
- **Multi-protocol**: Supports both SMB/CIFS and FTP connections
- **File Type Filtering**: Filter by images, videos, documents, etc.
- **Real-time Stats**: Monitor indexed files and connection status

## Installation

1. Clone or download this repository
2. Install Python 3.8+ if not already installed
3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your NAS settings:
```
NAS_IP=192.168.1.100  # Your NAS IP address
NAS_USERNAME=admin     # Your NAS username
NAS_PASSWORD=admin     # Your NAS password
SMB_SHARE_NAME=Public  # SMB share name
```

## Running the Application

```bash
python app/app.py
```

The application will be available at: `http://localhost:5000`

## Usage

1. **Search Files**: Enter keywords in the search box
2. **Filter Results**: Click file type chips to filter
3. **Browse Directories**: Click folder icons to navigate
4. **Preview Files**: Click preview button for images/text
5. **Download Files**: Click download button
6. **Update Index**: Click "Update Index" to refresh file list

## API Endpoints

- `GET /api/search?q=query` - Search files
- `GET /api/browse?path=/` - Browse directory
- `GET /api/download/<path>` - Download file
- `GET /api/preview/<path>` - Preview file
- `POST /api/index/update` - Update file index
- `GET /api/index/stats` - Get index statistics
- `GET /api/status` - System status

## Security Notes

- Change default NAS credentials immediately
- Use HTTPS in production environments
- Implement authentication for public access
- Set appropriate file size limits

## Requirements

- Python 3.8+
- iptime NAS2dual with SMB/FTP enabled
- Network access to NAS device

## Troubleshooting

1. **Connection Failed**: Check NAS IP and credentials
2. **SMB Issues**: Try using port 139 instead of 445
3. **FTP Issues**: Enable passive mode in settings
4. **Slow Search**: Reduce index depth or file count

## License

MIT License