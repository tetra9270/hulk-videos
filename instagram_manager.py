import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from config import Config

logger = logging.getLogger("InstagramReelsAutomation.InstagramManager")

class InstagramManager:
    API_VERSION = "v19.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

    def __init__(self):
        self.access_token = Config.INSTAGRAM_ACCESS_TOKEN
        self.ig_business_id = Config.INSTAGRAM_BUSINESS_ACCOUNT_ID
        
        # Configure a robust session with automatic retries for transient errors
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=2, # Wait 2s, 4s, 8s, 16s, 32s between retries
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _handle_response(self, response: requests.Response) -> dict:
        """Parses response and raises detailed error if status is not successful."""
        try:
            data = response.json()
        except ValueError:
            logger.error(f"Failed to parse API response as JSON: {response.text}")
            response.raise_for_status()
            return {}

        if "error" in data:
            err = data["error"]
            err_msg = (
                f"Instagram API Error: {err.get('message')} "
                f"(Code: {err.get('code')}, Subcode: {err.get('error_subcode')}, "
                f"Type: {err.get('type')}, TraceID: {err.get('fbtrace_id')})"
            )
            logger.error(err_msg)
            raise Exception(err_msg)

        response.raise_for_status()
        return data

    def test_connection(self) -> bool:
        """Validates credentials by fetching the IG Business Account info.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        url = f"{self.BASE_URL}/{self.ig_business_id}"
        params = {
            "fields": "username,name",
            "access_token": self.access_token
        }
        try:
            logger.info("Testing connection to Instagram Graph API...")
            response = self.session.get(url, params=params)
            data = self._handle_response(response)
            logger.info(f"Successfully connected! Authenticated as IG User: {data.get('username')} ({data.get('name')})")
            return True
        except Exception as e:
            logger.error(f"Instagram Graph API connection test failed: {e}")
            return False

    def create_reels_container(self, video_url: str, caption: str) -> str:
        """Creates an Instagram Reels media container for a video URL.
        
        Args:
            video_url: The public HTTPS URL of the video (e.g. on Cloudinary).
            caption: The text caption for the Reel.
            
        Returns:
            The creation ID (container ID).
        """
        url = f"{self.BASE_URL}/{self.ig_business_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true", # Share to both Reels tab and main Feed
            "access_token": self.access_token
        }
        
        logger.info("Initializing Reels container creation...")
        logger.debug(f"Payload (excluding token): { {k: v for k, v in payload.items() if k != 'access_token'} }")
        
        response = self.session.post(url, data=payload)
        data = self._handle_response(response)
        
        container_id = data.get("id")
        if not container_id:
            raise ValueError("No container ID returned in Instagram response.")
            
        logger.info(f"Reels container created successfully. Container ID: {container_id}")
        return container_id

    def check_container_status(self, container_id: str) -> dict:
        """Checks the status of the media container.
        
        Args:
            container_id: The ID of the container.
            
        Returns:
            Dict containing 'status_code'.
        """
        url = f"{self.BASE_URL}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self.access_token
        }
        
        response = self.session.get(url, params=params)
        data = self._handle_response(response)
        return data

    def poll_container_until_ready(self, container_id: str, timeout_seconds: int = 600, poll_interval_seconds: int = 15) -> bool:
        """Polls the container status until it is FINISHED, or fails.
        
        Args:
            container_id: The container ID to poll.
            timeout_seconds: Maximum time to wait before timing out (default 10 mins).
            poll_interval_seconds: Delay between status checks.
            
        Returns:
            True if ready, raises Exception if it failed or timed out.
        """
        logger.info(f"Waiting for video processing to complete (timeout: {timeout_seconds}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                status_info = self.check_container_status(container_id)
                status_code = status_info.get("status_code")
                
                logger.info(f"Current container status_code: {status_code}")
                
                if status_code == "FINISHED":
                    logger.info("Video processing finished and ready to publish.")
                    return True
                elif status_code == "ERROR":
                    err_msg = status_info.get("error_message") or "Unknown error during Instagram processing."
                    raise Exception(f"Instagram video processing failed: {err_msg}")
                elif status_code == "EXPIRED":
                    raise Exception("Instagram video container expired before publishing.")
                
            except Exception as e:
                # If it's a processing failure, propagate. If it's a network error during status check, log and retry.
                if "Instagram video processing failed" in str(e) or "container expired" in str(e):
                    raise
                logger.warning(f"Error checking container status (will retry): {e}")

            time.sleep(poll_interval_seconds)
            
        raise TimeoutError("Timed out waiting for Instagram to finish processing the video container.")

    def publish_reels_container(self, container_id: str) -> str:
        """Publishes the processed Reels container.
        
        Args:
            container_id: The ID of the completed container.
            
        Returns:
            The ID of the published media item.
        """
        url = f"{self.BASE_URL}/{self.ig_business_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self.access_token
        }
        
        logger.info(f"Publishing container ID {container_id} to Instagram Feed/Reels...")
        
        response = self.session.post(url, data=payload)
        data = self._handle_response(response)
        
        media_id = data.get("id")
        if not media_id:
            raise ValueError("No media ID returned in publish response.")
            
        logger.info(f"Reel successfully published! Media ID: {media_id}")
        return media_id
