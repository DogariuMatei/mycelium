"""
Autonomous orchestrator main entry point.

Manages the event loop for code synchronization and seedbox operations.
"""

import asyncio
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import Config
from modules import CodeSync, CodeSyncError, Seedbox, SeedboxError
from utils import setup_logger

logger = setup_logger(
    __name__,
    log_file=Config.LOG_DIR / "orchestrator.log",
    level=Config.LOG_LEVEL
)


class Orchestrator:
    """Main orchestrator for autonomous server operations."""

    def __init__(self):
        self.running = False
        self.code_sync = CodeSync(
            repo_path=Config.BASE_DIR,
            branch=Config.REPO_BRANCH
        )
        self.seedbox = Seedbox(
            content_dir=Config.CONTENT_DIR,
            tracker_url=Config.TORRENT_TRACKER,
            port_min=Config.SEEDBOX_PORT_MIN,
            port_max=Config.SEEDBOX_PORT_MAX
        )
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Configure handlers for shutdown."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self.running = False

    async def check_for_updates(self) -> None:
        """Periodic task to check for code updates."""
        while self.running:
            try:
                if self.code_sync.has_updates():
                    logger.info("Updates detected on remote repository")
                    self.code_sync.pull_updates()
                    logger.info("Updates pulled successfully, restarting")
                    sys.exit(Config.EXIT_RESTART)
            except CodeSyncError as e:
                logger.error(f"Code sync error: {e}")

            await asyncio.sleep(Config.UPDATE_CHECK_INTERVAL)

    async def heartbeat(self) -> None:
        """Periodic heartbeat logging."""
        while self.running:
            logger.info("Orchestrator Running")
            await asyncio.sleep(Config.HEARTBEAT_INTERVAL)

    async def run_seedbox(self) -> None:
        """Run seedbox in executor thread."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self.executor,
                self.seedbox.seed_content,
                Config.SEEDBOX_STATUS_INTERVAL
            )
        except SeedboxError as e:
            logger.error(f"Seedbox failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected seedbox error: {e}", exc_info=True)

    async def run(self) -> None:
        """Main orchestrator loop."""
        self.running = True
        logger.info("Orchestrator starting")
        logger.info(f"Repository: {Config.REPO_URL}")
        logger.info(f"Branch: {Config.REPO_BRANCH}")
        logger.info(f"Update check interval: {Config.UPDATE_CHECK_INTERVAL}s")
        logger.info(f"Content directory: {Config.CONTENT_DIR}")

        tasks = [
            asyncio.create_task(self.check_for_updates()),
            asyncio.create_task(self.heartbeat()),
            asyncio.create_task(self.run_seedbox()),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled, shutting down")
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self.executor.shutdown(wait=True)

        logger.info("Orchestrator stopped")


def main() -> int:
    """
    Application entry point.

    Returns:
        Exit code
    """
    try:
        Config.validate()
        orchestrator = Orchestrator()
        asyncio.run(orchestrator.run())
        return Config.EXIT_SUCCESS
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return Config.EXIT_SUCCESS
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return Config.EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
