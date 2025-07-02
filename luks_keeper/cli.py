import click
from .config import load_config
from .keys import PassphraseManager
from .devices import LUKSDevice
from .snaps import SnapshotManager

@click.group()
def cli():
    """
    luks-keeper: Secure LUKS passphrase manager and optional snapshot tool.
    """
    pass

@cli.command("key")
@click.argument("device")
@click.option(
    "--rotate",
    is_flag=True,
    help="Rotate (re-encrypt) the passphrase file for a device"
)
@click.option(
    "--config", "config_path",
    default=None,
    help="Path to config.yaml (default: ~/.config/luks-keeper/config.yaml)"
)
def manage_key(device: str, rotate: bool, config_path: str):
    """
    Ensure or rotate the encrypted LUKS passphrase file for DEVICE.
    """
    cfg = load_config(config_path)
    pm = PassphraseManager(cfg)

    if rotate:
        pm.rotate(device)
    else:
        pm.ensure_exists(device)

@cli.command("mount")
@click.option(
    "--config", "config_path",
    default=None,
    help="Path to config.yaml (default: ~/.config/luks-keeper/config.yaml)"
)
def mount_and_snapshot(config_path: str):
    """
    Open all LUKS devices, mount the first, prune old snapshots, and create a new one.
    """
    cfg = load_config(config_path)
    pm = PassphraseManager(cfg)

    # 1) Ensure every passphrase blob exists
    for dev in cfg.devices:
        pm.ensure_exists(dev.name)

    # 2) Open (decrypt) every LUKS device
    for dev in cfg.devices:
        LUKSDevice(dev, pm).open()

    # 3) Mount only the first device’s mapping (Btrfs RAID needs all peers opened)
    first = cfg.devices[0]
    if first.mount_point:
        LUKSDevice(first, pm).mount()

    # 4) If snapshot support is configured, prune old and create a new snapshot
    if cfg.snapshot_root and cfg.devices:
        source = cfg.devices[0].mount_point
        snaps = SnapshotManager(cfg.snapshot_root, cfg.retention_days)
        snaps.prune_old()
        new_snap = snaps.create_auto_snapshot(source)
        click.echo(f"Snapshot created at: {new_snap}")

    click.echo("All done.")

if __name__ == "__main__":
    cli()
