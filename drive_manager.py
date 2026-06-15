import os
import shutil
import logging
import re
import requests
from typing import List, Dict
from config import Config

logger = logging.getLogger("InstagramReelsAutomation.DriveManager")

class DriveManager:
    def __init__(self):
        """Initializes the DriveManager and determines the source mode."""
        self.api_key = Config.GOOGLE_API_KEY
        self.folder_id = Config.GOOGLE_DRIVE_FOLDER_ID
        self.local_dir = Config.VIDEOS_DIR
        
        if self.folder_id and self.api_key:
            self.mode = "drive_api"
            logger.info("DriveManager Mode: Google Drive official Web API (with API Key).")
        elif self.folder_id:
            self.mode = "drive_scrape"
            logger.info("DriveManager Mode: Google Drive Public HTML Scraper (No credentials needed!).")
        else:
            self.mode = "local"
            logger.info(f"DriveManager Mode: Local repository folder '{self.local_dir}' (No Google Cloud).")

    def list_videos(self) -> List[Dict[str, str]]:
        """Lists all video files depending on the active mode.
        
        Returns:
            List of dicts containing 'id', 'name', and 'mimeType'.
        """
        # --- MODE: LOCAL ---
        if self.mode == "local":
            videos = []
            if not os.path.exists(self.local_dir):
                os.makedirs(self.local_dir, exist_ok=True)
                
            for filename in os.listdir(self.local_dir):
                if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                    videos.append({
                        "id": filename,
                        "name": filename,
                        "mimeType": "video/mp4"
                    })
            videos.sort(key=lambda x: x.get('name', '').lower())
            logger.info(f"Found {len(videos)} video(s) in local '{self.local_dir}' folder.")
            return videos

        # --- MODE: DRIVE SCRAPE (No API Key) ---
        elif self.mode == "drive_scrape":
            url = f"https://drive.google.com/embeddedfolderview?id={self.folder_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            logger.info(f"Scraping public folder contents from URL: {url}")
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                html = response.text
                
                # Regex to extract Google Drive file ID and Title (Name)
                pattern = r'href="https://drive.google.com/file/d/([a-zA-Z0-9_-]+)/view[^>]*>.*?<div class="flip-entry-title">([^<]+)</div>'
                matches = re.findall(pattern, html, re.DOTALL)
                
                videos = []
                for file_id, name in matches:
                    # Filter for video files only
                    if name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                        videos.append({
                            "id": file_id,
                            "name": name,
                            "mimeType": "video/mp4"
                        })
                
                # Sort videos alphabetically by name
                videos.sort(key=lambda x: x.get('name', '').lower())
                logger.info(f"Found {len(videos)} video(s) in public Google Drive folder via HTML scraping.")
                return videos
            except Exception as e:
                logger.error(f"Failed to scrape public Google Drive folder contents: {e}", exc_info=True)
                raise

        # --- MODE: DRIVE API (With API Key) ---
        else:
            videos = []
            page_token = None
            url = "https://www.googleapis.com/drive/v3/files"
            query = f"'{self.folder_id}' in parents and mimeType contains 'video/' and trashed = false"

            try:
                while True:
                    params = {
                        'q': query,
                        'key': self.api_key,
                        'fields': 'nextPageToken, files(id, name, mimeType, createdTime)',
                        'pageSize': 100
                    }
                    if page_token:
                        params['pageToken'] = page_token

                    response = requests.get(url, params=params)
                    
                    if response.status_code == 403:
                        logger.error(
                            "Forbidden error. Please check that: \n"
                            "1. Your GOOGLE_API_KEY is correct.\n"
                            "2. The Google Drive folder is shared publicly: 'Anyone with the link can view'."
                        )
                    response.raise_for_status()
                    
                    data = response.json()
                    videos.extend(data.get('files', []))
                    
                    page_token = data.get('nextPageToken', None)
                    if not page_token:
                        break

                videos.sort(key=lambda x: (x.get('name', '').lower(), x.get('createdTime', '')))
                logger.info(f"Found {len(videos)} video(s) in Google Drive folder via API.")
                return videos

            except requests.exceptions.RequestException as e:
                logger.error(f"HTTP error occurred while listing Drive files: {e}")
                raise
            except Exception as e:
                logger.error(f"An unexpected error occurred while listing Drive files: {e}")
                raise

    def download_video(self, file_id: str, dest_path: str) -> str:
        """Retrieves the video depending on the active mode.
        
        Args:
            file_id: The ID of the file (Google Drive ID or local filename).
            dest_path: Destination path on local system.
            
        Returns:
            The local file path.
        """
        # --- MODE: LOCAL ---
        if self.mode == "local":
            local_src_path = os.path.join(self.local_dir, file_id)
            if not os.path.exists(local_src_path):
                raise FileNotFoundError(f"Local video file not found: {local_src_path}")
            
            logger.info(f"Copying local video '{file_id}' to temporary path: {dest_path}")
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(local_src_path, dest_path)
            return dest_path

        # --- MODE: DRIVE SCRAPE (No API Key) ---
        elif self.mode == "drive_scrape":
            logger.info(f"Downloading file ID: {file_id} from public Drive without API key...")
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            url = "https://docs.google.com/uc?export=download"
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            try:
                # 1. Initial request to trigger warning and fetch confirmation token in cookies
                response = session.get(url, params={'id': file_id}, stream=True)
                
                token = None
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        token = value
                        break
                
                # 2. Re-request with confirmation token if needed
                params = {'id': file_id, 'confirm': token} if token else {'id': file_id}
                response = session.get(url, params=params, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024 * 2): # 2MB chunks
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                                logger.info(f"Download Progress: {percent}%")
                                
                logger.info(f"Successfully downloaded to {dest_path}")
                return dest_path
            except Exception as e:
                logger.error(f"Failed to download public Drive file {file_id}: {e}", exc_info=True)
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                raise

        # --- MODE: DRIVE API (With API Key) ---
        else:
            logger.info(f"Starting API download of file ID: {file_id} to {dest_path}")
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            params = {
                "alt": "media",
                "key": self.api_key
            }

            try:
                response = requests.get(url, params=params, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024 * 2):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                                logger.info(f"Download Progress: {percent}%")
                
                logger.info(f"Successfully downloaded to {dest_path}")
                return dest_path
            except requests.exceptions.RequestException as e:
                logger.error(f"HTTP error downloading file {file_id}: {e}")
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                raise
            except Exception as e:
                logger.error(f"Unexpected error downloading file {file_id}: {e}")
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                raise
