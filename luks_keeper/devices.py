import os
import subprocess
from pathlib import Path
from .keys import PassphraseManager
from .config import AppConfig, DeviceConfig
from .hooks import run_hook
import click # Import click for secho

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
    """

    def __init__(
        self,
        global_config: AppConfig,
        device_config: DeviceConfig,
        passman: PassphraseManager,
    ):
        self.app_config = global_config
        self.config = device_config
        self.passman = passman

    def is_open(self) -> bool:
        """
        Check if the LUKS device is already opened.
        """
        result = subprocess.run(
            ["cryptsetup", "status", self.config.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0

    def open(self) -> None:
        """
        Open (decrypt) the LUKS device if not already open.
        """
        if not self.is_open():
            run_hook(self.app_config, "on_before_open", self.config)
            pw = self.passman.decrypt(self.config.name)
            cmd = _sudo_cmd([
                "cryptsetup", "luksOpen", self.config.devnode, self.config.name
            ])
            try:
                subprocess.run(
                    cmd,
                    input=pw + "\n",
                    text=True,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                # Check if the error is due to the device mapper name already existing
                if f"Device {self.config.name} already exists." in e.stderr:
                    click.secho(
                        f"Warning: Device mapper name '{self.config.name}' already exists "
                        "but is not reported as an open LUKS device. "
                        "Attempting to close it before re-opening.",
                        fg="yellow"
                    )
                    try:
                        # Attempt to close the conflicting device mapper entry
                        subprocess.run(_sudo_cmd(["cryptsetup", "luksClose", self.config.name]), check=True)
                        # Retry opening after closing
                        subprocess.run(
                            cmd,
                            input=pw + "\n",
                            text=True,
                            check=True,
                        )
                    except subprocess.CalledProcessError as retry_e:
                        click.secho(f"Error: Failed to open device '{self.config.name}' even after attempting to close a conflicting entry.", fg="red")
                        raise retry_e # Re-raise the error if retry fails
                else:
                    raise e # Re-raise other CalledProcessError
            run_hook(self.app_config, "on_after_open", self.config)

    def close(self) -> None:
        """
        Close (re-encrypt) the LUKS device if it's open.
        """
        if self.is_open():
            run_hook(self.app_config, "on_before_close", self.config)
            cmd = _sudo_cmd(["cryptsetup", "luksClose", self.config.name])
            subprocess.run(cmd, check=True)
            run_hook(self.app_config, "on_after_close", self.config)

    def is_mounted(self) -> bool:
        """
        Check if the device is already mounted at its mount point.
        """
        if not self.config.mount_point:
            return False
        return subprocess.run(
            ["mountpoint", "-q", self.config.mount_point]
        ).returncode == 0

    def mount(self) -> None:
        """
        Mount the opened device at the mount point, if configured.
        """
        if self.config.mount_point and not self.is_mounted():
            run_hook(self.app_config, "on_before_mount", self.config)
            Path(self.config.mount_point).mkdir(parents=True, exist_ok=True)
            cmd = _sudo_cmd([
                "mount", f"/dev/mapper/{self.config.name}", self.config.mount_point
            ])
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                click.secho(f"Error mounting device {self.config.name}: {e.stderr}", fg="red")
                raise e
            run_hook(self.app_config, "on_after_mount", self.config)

    def unmount(self) -> None:
        """
        Unmount the device from its mount point, if configured and mounted.
        """
        if self.config.mount_point and self.is_mounted():
            run_hook(self.app_config, "on_before_unmount", self.config)
            cmd = _sudo_cmd(["umount", self.config.mount_point])
            subprocess.run(cmd, check=True)
            run_hook(self.app_config, "on_after_unmount", self.config)

    def ensure_open_and_mounted(self) -> None:
        """
        Convenience method: open (decrypt) and mount the device.
        """
        self.open()
        self.mount()

    def ensure_unmounted_and_closed(self) -> None:
        """
        Convenience method: unmount and close (re-encrypt) the device.
        """
        self.unmount()
        self.close()
