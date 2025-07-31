# luks-keeper

**Secure LUKS passphrase manager** with built‑in Btrfs snapshot support. Built on PGP/GPG to safely encrypt your unlock passphrases on disk, and optionally prune and create automatic snapshots.

---

## Features

* **Key management**: encrypt & rotate LUKS passphrases per device under your PGP key.
* **Mount/Unmount workflow**: opens LUKS devices, mounts them, and unmounts and closes them cleanly.
* **Execution Hooks**: run custom scripts at any stage of the mount/unmount process.
* **Snapshot support**: prune old Btrfs snapshots and create timestamped, read-only snapshots.
* **Extensible**: class-based design ready to plug in remote key stores (Nostr, TOR, SSH, multisig).

---

## Installation

```bash
# inside your repo & venv
pip install -e .

# then you can run:
luks-keeper --help
```

---

## Configuration

Create a YAML config file at `~/.config/luks-keeper/config.yaml`:

```yaml
# LUKS devices to manage
devices:
  - name: crypt1
    devnode: /dev/nvme2n1p1
    mount_point: /mnt
  - name: crypt2
    devnode: /dev/nvme1n1p1
    mount_point: none # skip mounting (for example if crypt1 is a BTRFS RAID mount)

# (Optional) Btrfs automatic snapshots
snapshot_root: /mnt/_snapshots/automatic
# days to keep snapshots before pruning
retention_days: 30

# Where encrypted passphrases are stored
key_dir: ~/.luks-keeper/keys

# Your GPG key (email or ID)
gpg_recipient: you@example.com
```

> **Note**: Add this file before running commands, or the CLI will complain about a missing config.

---

## Usage

All commands are provided via the `luks-keeper` entrypoint.

### Key management

* **Ensure passphrase file exists** for `crypt1`:

  ```bash
  luks-keeper key crypt1
  ```

  Prompts for your LUKS passphrase and encrypts it under your PGP key.

* **Rotate** (re-encrypt) the passphrase file:

  ```bash
  luks-keeper key crypt1 --rotate
  ```

### Mount & Unmount

* **Mount all devices**:

  ```bash
  luks-keeper mount
  ```

  Opens all configured devices, mounts them, prunes old snapshots, and creates a new one.

* **Unmount all devices**:

  ```bash
  luks-keeper unmount
  ```

  Unmounts all configured devices and closes them.

---

## Execution Hooks

You can define custom scripts to run at various points in the mount/unmount process. Hooks can be defined globally or on a per-device basis.

### Configuration

```yaml
# Global hooks
hooks:
  on_before_mount_all: "echo 'Starting mount process...'"
  on_after_mount_all: "echo 'All devices mounted.'"

devices:
  - name: crypt1
    devnode: /dev/nvme2n1p1
    mount_point: /mnt
    hooks:
      on_after_mount: "/usr/local/bin/start-services.sh"
      on_before_unmount:
        command: "/usr/local/bin/stop-services.sh"
        ignore_errors: true
```

### Available Hooks

**Global Hooks:**

*   `on_before_mount_all`: Before any devices are opened or mounted.
*   `on_after_mount_all`: After all devices have been mounted.
*   `on_before_unmount_all`: Before any devices are unmounted.
*   `on_after_unmount_all`: After all devices have been closed.

**Device Hooks:**

*   `on_before_open`: Before a device is opened.
*   `on_after_open`: After a device is opened.
*   `on_before_mount`: Before a device is mounted.
*   `on_after_mount`: After a device is mounted.
*   `on_before_unmount`: Before a device is unmounted.
*   `on_after_unmount`: After a device is unmounted.
*   `on_before_close`: Before a device is closed.
*   `on_after_close`: After a device is closed.

### Error Handling

By default, if a hook command returns a non-zero exit code, the entire process will halt. You can override this by setting `ignore_errors: true` for the hook.

---

## Sudo Integration

To allow passwordless sudo for common operations, you can create a `/etc/sudoers.d/luks-keeper` file:

```text
# Allow your user to run luks-keeper filesystem commands without password
<your-username> ALL=(root) NOPASSWD: \
  /usr/bin/cryptsetup, \
  /usr/bin/mount, \
  /usr/bin/umount, \
  /usr/bin/btrfs
```

The CLI will detect if sudo is required and will just work whether or not you have passwordless sudo.

---

## Development & Extensibility

*   **Add new key stores** by implementing the `KeyStore` interface in `storage.py`.
*   **Support alternative CLI flags** or subcommands via `luks_keeper/cli.py` (using `click`).
*   **Add tests** under `tests/` using `pytest`.
