import os
import sys

# Force UTF-8 stdout/stderr to print emojis correctly on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from config import Config, ConfigError
from drive_manager import DriveManager
from cloudinary_manager import CloudinaryManager
from instagram_manager import InstagramManager
from scheduler import AutomationScheduler

# Setup main application logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("automation.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("InstagramReelsAutomation.Main")

# Helper: Load local history file
def load_history(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {"uploaded_files": {}}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"History file {file_path} is corrupted. Initializing new history.")
        return {"uploaded_files": {}}
    except Exception as e:
        logger.error(f"Error reading history file: {e}")
        return {"uploaded_files": {}}

# Helper: Save local history file
def save_history(file_path: str, history: Dict[str, Any]):
    try:
        # Write to a temporary file first, then rename to ensure atomicity
        temp_path = f"{file_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
        os.replace(temp_path, file_path)
    except Exception as e:
        logger.error(f"Failed to save history file: {e}")

# Helper: Read captions file
def get_caption_for_video(video_name: str, captions_path: str, history_count: int) -> str:
    """Selects a caption from captions.txt.
    
    Tries to find a caption tailored for the specific video file.
    Otherwise, picks one sequentially based on history count, or falls back to a default.
    """
    default_caption = f"Check out this reel! 🎥✨\n#instagram #reels #viral"
    
    if not os.path.exists(captions_path):
        logger.warning(f"Captions file '{captions_path}' not found. Using default caption.")
        return default_caption

    try:
        with open(captions_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        
        if not content:
            logger.warning(f"Captions file '{captions_path}' is empty. Using default caption.")
            return default_caption

        # Split captions by "---" separator (allows multi-line captions)
        if "---" in content:
            captions = [c.strip() for c in content.split("---") if c.strip()]
        else:
            # Fallback: split by double newlines
            captions = [c.strip() for c in content.split("\n\n") if c.strip()]

        if not captions:
            return default_caption

        # 1. Search for custom caption matching the video name prefix
        # Example format in captions.txt: "001_video.mp4: My custom caption!"
        for cap in captions:
            if cap.startswith(f"{video_name}:"):
                # Extract caption text after the filename
                caption_text = cap[len(video_name) + 1:].strip()
                logger.info(f"Found specific caption matching video name: {video_name}")
                return caption_text

        # 2. Sequential selection fallback: prevent repeating the same caption consecutively
        selected_index = history_count % len(captions)
        logger.info(f"Using sequential caption at index {selected_index} (total options: {len(captions)}).")
        return captions[selected_index]

    except Exception as e:
        logger.error(f"Error processing captions file: {e}")
        return default_caption

def run_pipeline(dry_run: bool = False):
    """Executes the complete Reel uploading pipeline."""
    logger.info(f"--- Pipeline Execution Started (Dry Run: {dry_run}) ---")
    
    # 1. Validate Configurations
    try:
        Config.load_and_validate()
    except ConfigError as ce:
        logger.critical(f"Configuration error: {ce}")
        sys.exit(1)
        
    # 2. Initialize Managers
    logger.info("Initializing API managers...")
    drive = DriveManager()
    cloudinary = CloudinaryManager()
    instagram = InstagramManager()
    
    # Check Instagram API access
    if not instagram.test_connection():
        logger.critical("Instagram API connection test failed. Aborting pipeline.")
        sys.exit(1)

    # 3. Load Upload History
    history = load_history(Config.HISTORY_FILE_PATH)
    uploaded_ids = history.get("uploaded_files", {})
    logger.info(f"Loaded upload history. Total successfully uploaded in history: {len(uploaded_ids)}")

    # 4. List and Select Video
    videos = drive.list_videos()
    
    # Filter out already uploaded files (by Drive File ID)
    unuploaded_videos = []
    for v in videos:
        file_id = v.get("id")
        file_name = v.get("name", "")
        
        # Skip if already in history
        if file_id in uploaded_ids:
            logger.debug(f"Skipping video '{file_name}' (ID: {file_id}) - Found in local history.")
            continue
            
        # Skip if already renamed with UPLOADED prefix in Drive
        if file_name.startswith("[UPLOADED]"):
            logger.debug(f"Skipping video '{file_name}' (ID: {file_id}) - Marked as uploaded in Google Drive.")
            # Auto-backfill local history for safety
            uploaded_ids[file_id] = {
                "name": file_name,
                "uploaded_at": datetime.now().isoformat(),
                "status": "backfilled_from_drive"
            }
            save_history(Config.HISTORY_FILE_PATH, history)
            continue
            
        unuploaded_videos.append(v)

    if not unuploaded_videos:
        logger.info("All videos in the Google Drive folder have already been uploaded! No work to do.")
        return

    # Select the next unuploaded video
    target_video = unuploaded_videos[0]
    video_id = target_video["id"]
    video_name = target_video["name"]
    logger.info(f"Selected video for upload: '{video_name}' (ID: {video_id})")

    # 5. Get caption
    caption = get_caption_for_video(video_name, Config.CAPTIONS_FILE_PATH, len(uploaded_ids))
    logger.info(f"Selected caption:\n{caption}\n")

    # Local file path for temporary download
    local_path = os.path.join(Config.TEMP_DOWNLOAD_DIR, video_name)
    cloudinary_url = None
    container_id = None
    media_id = None

    try:
        if dry_run:
            logger.info("[DRY RUN] Simulating video download...")
            logger.info(f"[DRY RUN] Would download video ID {video_id} to {local_path}")
            logger.info("[DRY RUN] Simulating Cloudinary upload...")
            mock_url = "https://res.cloudinary.com/demo/video/upload/dog.mp4"
            logger.info(f"[DRY RUN] Mock Cloudinary URL: {mock_url}")
            logger.info("[DRY RUN] Simulating Instagram Reel Container creation...")
            logger.info(f"[DRY RUN] Caption: {caption}")
            logger.info("[DRY RUN] Simulating publish and status checks...")
            logger.info("[DRY RUN] Dry run finished successfully.")
            return

        # 6. Download Video
        drive.download_video(video_id, local_path)

        # 7. Upload to Cloudinary
        cloudinary_url = cloudinary.upload_video(local_path)

        # 8. Create Instagram Reels Container
        container_id = instagram.create_reels_container(cloudinary_url, caption)

        # 9. Wait for Instagram processing
        instagram.poll_container_until_ready(container_id)

        # 10. Publish Reel
        media_id = instagram.publish_reels_container(container_id)

        # 11. Record in History & Save
        uploaded_ids[video_id] = {
            "name": video_name,
            "uploaded_at": datetime.now().isoformat(),
            "cloudinary_url": cloudinary_url,
            "instagram_media_id": media_id,
            "status": "published"
        }
        save_history(Config.HISTORY_FILE_PATH, history)
        logger.info(f"Recorded video '{video_name}' in history.json")

        # 12. State tracking is done via history.json. Google Drive modification is skipped.
        logger.info("Upload recorded in history.json. Skipping Google Drive folder modifications.")

        logger.info(f"Successfully processed and published Reel for '{video_name}'!")

    except Exception as e:
        logger.error(f"Pipeline failed at step processing '{video_name}': {e}", exc_info=True)
        raise e

    finally:
        # Cleanup local downloaded video to prevent filling up disk space
        if os.path.exists(local_path):
            try:
                logger.info(f"Cleaning up local file: {local_path}")
                os.remove(local_path)
                logger.info("Local cleanup complete.")
            except Exception as ce:
                logger.error(f"Failed to delete local temporary video file {local_path}: {ce}")


def main():
    parser = argparse.ArgumentParser(description="Instagram Reels Daily Automation System")
    parser.add_argument(
        "--single-run", 
        action="store_true", 
        default=True,
        help="Run the upload pipeline once and exit immediately (default)"
    )
    parser.add_argument(
        "--daemon", 
        action="store_true", 
        help="Run the system in daemon mode, scheduling a daily upload"
    )
    parser.add_argument(
        "--time", 
        type=str, 
        default="10:00,12:00,15:00,18:00,22:00", 
        help="Scheduled times for uploads in comma-separated HH:MM format (default: 10:00,12:00,15:00,18:00,22:00). Used only with --daemon"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Run the check and download logic without uploading to Cloudinary or publishing to Instagram"
    )
    
    # If daemon is passed, we disable single-run default
    args = parser.parse_args()
    if args.daemon:
        args.single_run = False

    logger.info("Starting Instagram Reels Automation Command-line Application.")
    
    # Initialize Scheduler
    scheduler = AutomationScheduler(lambda: run_pipeline(dry_run=args.dry_run))

    if args.daemon:
        scheduler.run_daemon(times_str=args.time)
    else:
        scheduler.run_once()

if __name__ == "__main__":
    main()
