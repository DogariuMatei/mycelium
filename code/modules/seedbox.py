"""
BitTorrent seeding operations.

"""

import glob
import os
import time
from pathlib import Path
from typing import List, Tuple

import libtorrent as lt

from utils import setup_logger

logger = setup_logger(__name__)


class SeedboxError(Exception):
    pass


class Seedbox:
    """BitTorrent seeding operations for content distribution."""

    def __init__(
        self,
        content_dir: Path,
        tracker_url: str,
        port_min: int = 6881,
        port_max: int = 6891
    ):

        self.content_dir = Path(content_dir)
        self.tracker_url = tracker_url
        self.port_min = port_min
        self.port_max = port_max
        self.session = None
        self.handles: List[Tuple[lt.torrent_handle, str]] = []

    def _create_torrent(self, file_path: Path) -> Path:
        """
        Create torrent file from filepath

        Args:
            file_path: Path to-be-torrent file

        Returns:
            Path to .torrent file
        """
        torrent_file = Path(str(file_path) + ".torrent")

        if torrent_file.exists():
            logger.debug(f"Torrent already exists: {torrent_file.name}")
            return torrent_file

        logger.info(f"Creating torrent for: {file_path.name}")

        fs = lt.file_storage()
        lt.add_files(fs, str(file_path))

        t = lt.create_torrent(fs)
        t.add_tracker(self.tracker_url)
        t.set_creator("Mycelium Autonomous Seedbox")

        lt.set_piece_hashes(t, str(file_path.parent))
        torrent = t.generate()

        with open(torrent_file, "wb") as f:
            f.write(lt.bencode(torrent))

        logger.info(f"Torrent created: {torrent_file.name}")
        return torrent_file

    def _initialize_session(self) -> None:
        """Initialize libtorrent session"""
        self.session = lt.session()
        self.session.listen_on(self.port_min, self.port_max)

        settings = self.session.get_settings()
        settings['listen_interfaces'] = f'0.0.0.0:{self.port_min}'
        self.session.apply_settings(settings)

        logger.info(f"Session initialized on ports {self.port_min}-{self.port_max}")

    def _load_content_files(self) -> List[Path]:
        """
        Load content files from directory

        Returns:
            List of file paths to seed
        """
        if not self.content_dir.exists():
            raise SeedboxError(f"Content directory not found: {self.content_dir}")

        files = glob.glob(str(self.content_dir / "*"))
        files = [Path(f) for f in files if not f.endswith('.torrent')]

        if not files:
            raise SeedboxError(f"No files found in: {self.content_dir}")

        logger.info(f"Found {len(files)} files to seed")
        return files

    def _add_torrents(self, files: List[Path]) -> None:
        """
        Create and add torrents to session

        Args:
            files: List of files to create torrents for
        """
        for file_path in files:
            try:
                torrent_file = self._create_torrent(file_path)
                info = lt.torrent_info(str(torrent_file))
                handle = self.session.add_torrent({
                    'ti': info,
                    'save_path': str(file_path.parent)
                })
                self.handles.append((handle, file_path.name))
                logger.info(f"Added to session: {file_path.name}")
            except Exception as e:
                logger.error(f"Failed to add {file_path.name}: {e}")

    def get_status(self) -> dict:
        """
        Get current seeding status

        Returns:
            Dictionary with status information
        """
        if not self.handles:
            return {"active": False, "torrents": 0, "peers": 0, "uploaded": 0}

        total_upload = 0
        total_peers = 0

        for handle, _ in self.handles:
            status = handle.status()
            total_upload += status.total_upload
            total_peers += status.num_peers

        return {
            "active": True,
            "torrents": len(self.handles),
            "peers": total_peers,
            "uploaded": total_upload
        }

    def seed_content(self, status_interval: int = 5) -> None:
        """
        Main seeding loop

        Args:
            status_interval: Seconds between status updates

        Raises:
            SeedboxError: If initialization fails
        """
        try:
            logger.info("Starting seedbox")
            logger.info(f"Content directory: {self.content_dir}")
            logger.info(f"Tracker: {self.tracker_url}")

            self._initialize_session()
            files = self._load_content_files()
            self._add_torrents(files)

            if not self.handles:
                raise SeedboxError("No torrents loaded")

            logger.info(f"Seeding {len(self.handles)} torrents")

            while True:
                status = self.get_status()
                logger.info(
                    f"Seeding: {status['torrents']} torrents, "
                    f"{status['peers']} peers, "
                    f"{status['uploaded'] / 1024 / 1024:.1f} MB uploaded"
                )
                time.sleep(status_interval)

        except KeyboardInterrupt:
            logger.info("Seedbox interrupted")
        except Exception as e:
            logger.error(f"Seedbox error: {e}", exc_info=True)
            raise SeedboxError(f"Seeding failed: {e}")
        finally:
            if self.session:
                logger.info("Stopping seedbox")
