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
@click.option("--rotate", is_flag=True, help="Rotate encrypted passphrase for a device")
@click.option("--config", "config_path", default=None,
              help="Path to config.yaml (default reads from ~/.config/luks-keeper)")
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
@click.option("--config", "config_path", default=None,
              help="Path to config.yaml (default reads from ~/.config/luks-keeper)")
def mount_and_snapshot(config_path: str):
    """
    Open & mount all LUKS devices, prune old snapshots, and create a new one.
    """
    cfg = load_config(config_path)
    pm = PassphraseManager(cfg)

    # Open and mount each device
    for dev_cfg in cfg.devices:
        device = LUKSDevice(dev_cfg, pm)
        device.ensure_open_and_mounted()

    # If snapshot_root is configured, run pruning and snapshotting
    if cfg.snapshot_root and cfg.devices:
        # Use the first device's mount_point as the snapshot source
        source = cfg.devices[0].mount_point
        snaps = SnapshotManager(cfg.snapshot_root, cfg.retention_days)
        snaps.prune_old()
        new_snap = snaps.create_auto_snapshot(source)
        click.echo(f"Snapshot created at: {new_snap}")

    click.echo("All done.")

if __name__ == "__main__":
    cli()
