# luks-keeper

**Secure LUKS passphrase manager** with built‑in Btrfs snapshot support. Built on PGP/GPG to safely encrypt your unlock passphrases on disk, and optionally prune and create automatic snapshots.

---

## Features

* **Key management**: encrypt & rotate LUKS passphrases per device under your PGP key.
* **Mount workflow**: opens LUKS devices, mounts them (with optional sudo), and handles multiple devices.
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

### Mount & Snapshot

Opens all configured devices, mounts them, prunes old snapshots, and creates a new one:

```bash
luks-keeper mount
```

* Will prompt for sudo if needed.
* Deletes any auto-snapshots older than `retention_days`.
* Creates a new read-only snapshot under `snapshot_root/YYYY-MM-DD_hh-mm-ss`.

---

## Sudo Integration

To allow passwordless sudo for common operations, you can create a `/etc/sudoers.d/luks-keeper` file:

```text
# Allow your user to run luks-keeper filesystem commands without password
<your-username> ALL=(root) NOPASSWD: \
  /usr/bin/cryptsetup, \
  /usr/bin/mount, \
  /usr/bin/btrfs
```

The CLI will detect if sudo is required and will just work whether or not you have passwordless sudo.

---

## Development & Extensibility

* **Add new key stores** by implementing the `KeyStore` interface in `storage.py`.
* **Support alternative CLI flags** or subcommands via `luks_keeper/cli.py` (using `click`).
* **Add tests** under `tests/` using `pytest`.
