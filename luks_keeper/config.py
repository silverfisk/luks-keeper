import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict

# Default location for config file
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "luks-keeper" / "config.yaml"

@dataclass
class HookConfig:
    command: str
    ignore_errors: bool = False

@dataclass
class DeviceConfig:
    name: str
    devnode: str
    mount_point: Optional[str]  # None or "none" to skip mounting
    hooks: Dict[str, HookConfig] = field(default_factory=dict)

@dataclass
class AppConfig:
    devices: List[DeviceConfig]
    snapshot_root: Optional[str]
    retention_days: int
    key_dir: str
    gpg_recipient: str
    hooks: Dict[str, HookConfig] = field(default_factory=dict)

def _parse_hooks(data: dict) -> Dict[str, HookConfig]:
    """Parse a dictionary of hooks into HookConfig objects."""
    hooks = {}
    for name, hook_data in data.items():
        if isinstance(hook_data, str):
            hooks[name] = HookConfig(command=hook_data)
        elif isinstance(hook_data, dict):
            hooks[name] = HookConfig(
                command=hook_data["command"],
                ignore_errors=hook_data.get("ignore_errors", False),
            )
    return hooks

def load_config(path: Optional[str] = None) -> AppConfig:
    """Load YAML config from DEFAULT_CONFIG_PATH or given path."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {cfg_path}"
        )
    with open(cfg_path, "r") as f:
        data = yaml.safe_load(f)

    devices = []
    for d in data.get("devices", []):
        mp = d.get("mount_point")
        # Treat "none" or empty as no mount
        mp = None if mp in (None, "none", "") else mp
        devices.append(DeviceConfig(
            name=d["name"],
            devnode=d["devnode"],
            mount_point=mp,
            hooks=_parse_hooks(d.get("hooks", {})),
        ))

    return AppConfig(
        devices=devices,
        snapshot_root=data.get("snapshot_root"),
        retention_days=int(data.get("retention_days", 30)),
        key_dir=os.path.expanduser(data.get("key_dir", "~/.luks-keeper/keys")),
        gpg_recipient=data["gpg_recipient"],
        hooks=_parse_hooks(data.get("hooks", {})),
    )
