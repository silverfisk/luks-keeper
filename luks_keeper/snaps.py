import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta


def _sudo_cmd(cmd: list) -> list:
    """
    Prepend 'sudo' to the command if not running as root.
    """
    if os.geteuid() != 0:
        return ['sudo'] + cmd
    return cmd

class SnapshotManager:
    """
    Manages Btrfs snapshots: pruning old ones and creating new read-only snapshots.

    Attributes:
        base_path (Path): Directory where automatic snapshots are stored.
        retention_days (int): Days to keep snapshots before pruning.
    """

    def __init__(self, base_path: str, retention_days: int):
        self.base_path = Path(base_path)
        self.retention_days = retention_days
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def prune_old(self) -> None:
        """
        Delete snapshots older than retention_days.
        """
        now = datetime.now()
        for sub in self.base_path.iterdir():
            if not sub.is_dir():
                continue
            # Expect directory names like YYYY-MM-DD_hh-mm-ss
            try:
                ts = datetime.strptime(sub.name, "%Y-%m-%d_%H-%M-%S")
            except ValueError:
                # Skip non-timestamped dirs
                continue
            age = now - ts
            if age > timedelta(days=self.retention_days):
                print(f"Deleting old snapshot: {sub}")
                cmd = _sudo_cmd(["btrfs", "subvolume", "delete", str(sub)])
                subprocess.run(cmd, check=True)

    def create_auto_snapshot(self, source: str) -> str:
        """
        Create a new read-only snapshot of source at base_path/YYYY-MM-DD_hh-mm-ss.
        Returns:
            str: Path of the created snapshot.
        """
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dest = self.base_path / ts
        print(f"Creating snapshot: {dest}")
        cmd = _sudo_cmd([
            "btrfs", "subvolume", "snapshot", "-r", source, str(dest)
        ])
        subprocess.run(cmd, check=True)
        return str(dest)
