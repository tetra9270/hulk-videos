import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the current directory or parent directory
load_dotenv()

class ConfigError(Exception):
    """Exception raised for errors in the configuration."""
    pass

class Config:
    # Environment variables (initialized to defaults/empty)
    FACEBOOK_APP_ID = ""
    FACEBOOK_APP_SECRET = ""
    INSTAGRAM_ACCESS_TOKEN = ""
    INSTAGRAM_BUSINESS_ACCOUNT_ID = ""
    
    CLOUDINARY_CLOUD_NAME = ""
    CLOUDINARY_API_KEY = ""
    CLOUDINARY_API_SECRET = ""
    
    GOOGLE_DRIVE_FOLDER_ID = ""
    GOOGLE_API_KEY = ""
    
    # App Settings
    HISTORY_FILE_PATH = "history.json"
    CAPTIONS_FILE_PATH = "captions.txt"
    
    # Temporary download directory
    TEMP_DOWNLOAD_DIR = "temp_downloads"
    
    @classmethod
    def load_and_validate(cls):
        """Loads and validates all environment variables."""
        # Force reload from environment
        load_dotenv()
        
        cls.FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
        cls.FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
        
        cls.INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        if not cls.INSTAGRAM_ACCESS_TOKEN:
            raise ConfigError("Missing required environment variable: INSTAGRAM_ACCESS_TOKEN")
            
        cls.INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        if not cls.INSTAGRAM_BUSINESS_ACCOUNT_ID:
            raise ConfigError("Missing required environment variable: INSTAGRAM_BUSINESS_ACCOUNT_ID")
            
        cls.CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
        if not cls.CLOUDINARY_CLOUD_NAME:
            raise ConfigError("Missing required environment variable: CLOUDINARY_CLOUD_NAME")
            
        cls.CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
        if not cls.CLOUDINARY_API_KEY:
            raise ConfigError("Missing required environment variable: CLOUDINARY_API_KEY")
            
        cls.CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
        if not cls.CLOUDINARY_API_SECRET:
            raise ConfigError("Missing required environment variable: CLOUDINARY_API_SECRET")
            
        cls.GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
        cls.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
        
        # Local videos directory fallback if Google Drive is not used
        cls.VIDEOS_DIR = os.getenv("VIDEOS_DIR", "videos")
        
        cls.HISTORY_FILE_PATH = os.getenv("HISTORY_FILE_PATH", "history.json")
        cls.CAPTIONS_FILE_PATH = os.getenv("CAPTIONS_FILE_PATH", "captions.txt")
        cls.TEMP_DOWNLOAD_DIR = os.getenv("TEMP_DOWNLOAD_DIR", "temp_downloads")
        
        # Ensure temporary download and local videos directories exist
        os.makedirs(cls.TEMP_DOWNLOAD_DIR, exist_ok=True)
        os.makedirs(cls.VIDEOS_DIR, exist_ok=True)



