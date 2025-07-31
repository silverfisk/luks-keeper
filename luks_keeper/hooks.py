import subprocess
import click
from typing import List, Optional
from .config import HookConfig, AppConfig, DeviceConfig

class HookExecutionError(Exception):
    """Custom exception for failed hook execution."""
    pass

def _run_command(command: str, ignore_errors: bool):
    """
    Executes a single shell command.
    """
    try:
        subprocess.run(
            command,
            shell=True,
            check=not ignore_errors,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        click.secho(f"Error executing command: {command}", fg="red")
        click.secho(f"STDOUT: {e.stdout}", fg="red")
        click.secho(f"STDERR: {e.stderr}", fg="red")
        raise HookExecutionError(
            f"Command '{command}' failed with exit code {e.returncode}"
        ) from e

def run_hook(
    config: AppConfig,
    hook_name: str,
    device: Optional[DeviceConfig] = None,
):
    """
    Run a specific hook by name, checking both global and device-specific hooks.
    """
    # Global hook
    if hook_name in config.hooks:
        hook = config.hooks[hook_name]
        click.echo(f"Running global hook '{hook_name}': {hook.command}")
        _run_command(hook.command, hook.ignore_errors)

    # Device-specific hook
    if device and hook_name in device.hooks:
        hook = device.hooks[hook_name]
        click.echo(f"Running device hook '{hook_name}' for {device.name}: {hook.command}")
        _run_command(hook.command, hook.ignore_errors)