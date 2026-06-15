import time
import logging
import schedule
from typing import Callable

logger = logging.getLogger("InstagramReelsAutomation.Scheduler")

class AutomationScheduler:
    def __init__(self, task_func: Callable):
        """Initializes the scheduler with the task function to execute.
        
        Args:
            task_func: The pipeline execution function to run.
        """
        self.task_func = task_func

    def run_once(self):
        """Runs the pipeline execution immediately and finishes."""
        logger.info("Running automation system in single-run mode.")
        try:
            self.task_func()
        except Exception as e:
            logger.error(f"Single-run execution failed: {e}", exc_info=True)
            raise

    def run_daemon(self, times_str: str = "10:00,12:00,15:00,18:00,22:00"):
        """Schedules the pipeline execution to run daily at multiple specified local times.
        
        Args:
            times_str: Comma-separated daily scheduled times (e.g., '10:00,15:00,18:00,22:00').
        """
        times = [t.strip() for t in times_str.split(",") if t.strip()]
        logger.info(f"Configuring scheduler daemon to run daily at: {', '.join(times)} (local system time).")
        
        # Schedule the task for each specified time
        for time_str in times:
            schedule.every().day.at(time_str).do(self._safe_execute)
            logger.info(f"Scheduled upload time: {time_str}")
        
        logger.info("Scheduler loop started. Waiting for scheduled triggers...")
        try:
            while True:
                schedule.run_pending()
                time.sleep(10) # Wake up every 10 seconds to check schedules
        except KeyboardInterrupt:
            logger.info("Scheduler daemon stopped by user (Ctrl+C).")
        except Exception as e:
            logger.error(f"Scheduler daemon stopped due to unhandled error: {e}", exc_info=True)
            raise

    def _safe_execute(self):
        """Executes the task wrapper with try-except to prevent the daemon from crashing on errors."""
        logger.info("--- Scheduled execution triggered ---")
        start_time = time.time()
        try:
            self.task_func()
            duration = time.time() - start_time
            logger.info(f"--- Scheduled execution finished successfully in {duration:.2f} seconds ---")
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"--- Scheduled execution failed after {duration:.2f} seconds. Error: {e} ---", exc_info=True)
