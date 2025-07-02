import os
import subprocess
from pathlib import Path
from .keys import PassphraseManager
from .config import DeviceConfig


def _sudo_cmd(cmd: list) -> list:
    """
    Prepend 'sudo' to the command if not running as root.
    """
    if os.geteuid() != 0:
        return ["sudo"] + cmd
    return cmd


class LUKSDevice:
    """
    Represents a LUKS-encrypted block device that can be opened and mounted.

    Attributes:
        config (DeviceConfig): Device configuration.
        passman (PassphraseManager): Passphrase manager to decrypt LUKS key.
    """

    def __init__(self, config: DeviceConfig, passman: PassphraseManager):
        self.name = config.name
        self.devnode = config.devnode
        self.mount_point = config.mount_point
        self.passman = passman

    def is_open(self) -> bool:
        """
        Check if the LUKS device is already opened.
        """
        result = subprocess.run(
            ["cryptsetup", "status", self.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0

    def open(self) -> None:
        """
        Open (decrypt) the LUKS device if not already open.
        Prompts GPG for passphrase decryption.
        """
        if not self.is_open():
            # Decrypt passphrase
            pw = self.passman.decrypt(self.name)
            # Open with cryptsetup
            cmd = _sudo_cmd([
                "cryptsetup", "luksOpen", self.devnode, self.name
            ])
            subprocess.run(
                cmd,
                input=pw + "\n",
                text=True,
                check=True,
            )

    def is_mounted(self) -> bool:
        """
        Check if the device is already mounted at its mount point.
        """
        if not self.mount_point:
            return False
        return subprocess.run(
            ["mountpoint", "-q", self.mount_point]
        ).returncode == 0

    def mount(self) -> None:
        """
        Mount the opened device at the mount point, if configured.
        """
        if self.mount_point and not self.is_mounted():
            Path(self.mount_point).mkdir(parents=True, exist_ok=True)
            cmd = _sudo_cmd([
                "mount", f"/dev/mapper/{self.name}", self.mount_point
            ])
            subprocess.run(cmd, check=True)

    def ensure_open_and_mounted(self) -> None:
        """
        Convenience method: open (decrypt) and mount the device.
        """
        self.open()
        self.mount()
