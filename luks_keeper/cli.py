import click
from .config import load_config
from .keys import PassphraseManager
from .devices import LUKSDevice
from .snaps import SnapshotManager
from .hooks import run_hook, HookExecutionError

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
    Open all LUKS devices, mount them, and create snapshots if configured.
    """
    try:
        cfg = load_config(config_path)
        pm = PassphraseManager(cfg)

        # 1) Run global pre-mount hook
        run_hook(cfg, "on_before_mount_all")

        # 2) Ensure passphrases exist and open each device
        for dev_cfg in cfg.devices:
            pm.ensure_exists(dev_cfg.name)
            LUKSDevice(cfg, dev_cfg, pm).open()

        # 3) Mount each device
        for dev_cfg in cfg.devices:
            LUKSDevice(cfg, dev_cfg, pm).mount()

        # 4) If snapshot support is configured, prune old and create a new snapshot
        if cfg.snapshot_root and cfg.devices:
            source = cfg.devices[0].mount_point
            snaps = SnapshotManager(cfg.snapshot_root, cfg.retention_days)
            snaps.prune_old()
            new_snap = snaps.create_auto_snapshot(source)
            click.echo(f"Snapshot created at: {new_snap}")

        # 5) Run global post-mount hook
        run_hook(cfg, "on_after_mount_all")
        click.secho("All devices mounted successfully.", fg="green")

    except (FileNotFoundError, HookExecutionError) as e:
        click.secho(f"Error: {e}", fg="red")
        exit(1)

@cli.command("unmount")
@click.option(
    "--config", "config_path",
    default=None,
    help="Path to config.yaml (default: ~/.config/luks-keeper/config.yaml)"
)
def unmount_all(config_path: str):
    """
    Unmount and close all LUKS devices.
    """
    try:
        cfg = load_config(config_path)
        pm = PassphraseManager(cfg)

        # 1) Run global pre-unmount hook
        run_hook(cfg, "on_before_unmount_all")

        # 2) Unmount each device (in reverse order)
        for dev_cfg in reversed(cfg.devices):
            LUKSDevice(cfg, dev_cfg, pm).unmount()

        # 3) Close each device (in reverse order)
        for dev_cfg in reversed(cfg.devices):
            LUKSDevice(cfg, dev_cfg, pm).close()

        # 4) Run global post-unmount hook
        run_hook(cfg, "on_after_unmount_all")
        click.secho("All devices unmounted successfully.", fg="green")

    except (FileNotFoundError, HookExecutionError) as e:
        click.secho(f"Error: {e}", fg="red")
        exit(1)

if __name__ == "__main__":
    cli()
