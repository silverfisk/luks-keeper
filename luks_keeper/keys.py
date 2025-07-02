import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
import getpass

from .config import AppConfig

class KeyStore(ABC):
    """Abstract interface for key storage backends."""
    @abstractmethod
    def exists(self, name: str) -> bool:
        ...
    @abstractmethod
    def get(self, name: str) -> str:
        """Decrypt and return plaintext."""
        ...
    @abstractmethod
    def set(self, name: str, plaintext: str) -> None:
        """Encrypt and store plaintext."""
        ...

class FileKeyStore(KeyStore):
    """Local filesystem key-store using GPG."""
    def __init__(self, key_dir: str, gpg_recipient: str):
        self.dir = Path(os.path.expanduser(key_dir))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.recipient = gpg_recipient

    def _path(self, name: str) -> Path:
        return self.dir / f"luks-pass_{name}.gpg"

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

    def get(self, name: str) -> str:
        path = str(self._path(name))
        result = subprocess.run(
            ["gpg", "--quiet", "--batch", "--decrypt", path],
            capture_output=True, check=True
        )
        return result.stdout.decode().strip()

    def set(self, name: str, plaintext: str) -> None:
        path = str(self._path(name))
        # --yes to overwrite, --pinentry-mode=loopback if you want loopback prompting
        subprocess.run(
            [
                "gpg", "--batch", "--yes",
                "--encrypt", "--recipient", self.recipient,
                "--output", path
            ],
            input=plaintext.encode(),
            check=True
        )

class PassphraseManager:
    """Handles creation, rotation, and decryption of LUKS passphrases."""

    def __init__(self, config: AppConfig):
        self.store = FileKeyStore(config.key_dir, config.gpg_recipient)

    def ensure_exists(self, device: str):
        """If no keyfile exists for `device`, prompt & create it."""
        if not self.store.exists(device):
            pw = getpass.getpass(f"Enter LUKS passphrase for '{device}': ")
            self.store.set(device, pw)
            print(f"Encrypted keyfile created for '{device}'")

    def rotate(self, device: str):
        """Force overwrite of an existing keyfile (with confirmation)."""
        if self.store.exists(device):
            ans = input(f"Overwrite keyfile for '{device}'? [y/N]: ")
            if ans.lower() != "y":
                print("Aborted rotation.")
                return
        pw = getpass.getpass(f"Enter new LUKS passphrase for '{device}': ")
        self.store.set(device, pw)
        print(f"Keyfile for '{device}' has been rotated.")

    def decrypt(self, device: str) -> str:
        """Return the plaintext passphrase for `device` (prompts GPG)."""
        return self.store.get(device)
