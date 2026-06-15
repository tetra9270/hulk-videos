import logging
import cloudinary
import cloudinary.uploader
from config import Config

logger = logging.getLogger("InstagramReelsAutomation.CloudinaryManager")

class CloudinaryManager:
    def __init__(self):
        """Initializes and configures the Cloudinary SDK using credentials from config."""
        try:
            cloudinary.config(
                cloud_name=Config.CLOUDINARY_CLOUD_NAME,
                api_key=Config.CLOUDINARY_API_KEY,
                api_secret=Config.CLOUDINARY_API_SECRET,
                secure=True
            )
            logger.info("Cloudinary configured successfully.")
        except Exception as e:
            logger.error(f"Failed to configure Cloudinary: {e}")
            raise

    def upload_video(self, file_path: str) -> str:
        """Uploads a video to Cloudinary using chunked upload.
        
        Args:
            file_path: The local path to the video file.
            
        Returns:
            The secure (HTTPS) URL of the uploaded video.
        """
        logger.info(f"Uploading video {file_path} to Cloudinary...")
        
        try:
            # We use upload_large to handle potentially large files (above 20MB) reliably in chunks.
            # resource_type='video' is required for video files.
            response = cloudinary.uploader.upload_large(
                file_path,
                resource_type="video",
                chunk_size=6000000, # ~6MB chunks
                # We can also add some tags to easily identify uploads in Cloudinary console
                tags=["instagram_reels_automation"]
            )
            
            secure_url = response.get("secure_url")
            if not secure_url:
                raise ValueError("Upload succeeded but secure_url was not returned in Cloudinary response.")
            
            logger.info(f"Cloudinary upload successful. Secure URL: {secure_url}")
            return secure_url
            
        except Exception as e:
            logger.error(f"Cloudinary upload failed for file {file_path}: {e}", exc_info=True)
            raise
            
    def delete_video(self, public_id: str):
        """Optionally deletes a video from Cloudinary to save space after publication.
        
        Args:
            public_id: The public ID of the resource in Cloudinary.
        """
        logger.info(f"Deleting video with public ID: {public_id} from Cloudinary.")
        try:
            cloudinary.uploader.destroy(public_id, resource_type="video")
            logger.info("Deletion completed.")
        except Exception as e:
            logger.warning(f"Failed to delete video from Cloudinary (public ID: {public_id}): {e}")
