# cfgsync

`cfgsync` is a small CLI for managing application config files in one local vault and syncing that vault to an object store such as Cloudflare R2.

It is intended for configs like Ghostty, Codex, Claude, Hermes, shell files, editor settings, and other dotfiles that you want to version, restore, or install on a new machine without hand-copying directories.

## Features

- Track individual files, symlinks, or whole directories.
- Store configs in a normalized local vault under `~/.local/share/cfgsync`.
- Install tracked configs back to their original locations with symlinks.
- Back up existing files before replacing them during install.
- Push and pull the vault through S3-compatible storage, including Cloudflare R2.
- Keep remote credentials out of the manifest by reading them from environment variables.
- Show status and file diffs before changing anything.
- Use dry-run mode for install and remote sync operations.
- Ship as a Python package with a `cfgsync` console command.

## How It Works

`cfgsync` keeps a manifest and copied config content in a vault:

```text
~/.local/share/cfgsync/
  manifest.json
  items/
    ghostty/
    codex/
    claude/
    hermes/
```

When you run `cfgsync add ghostty ~/.config/ghostty`, the source path is copied into `items/ghostty` and recorded in `manifest.json`.

When you run `cfgsync install`, the original source path is replaced by a symlink back to the vaulted copy. If the source path already exists, `cfgsync` creates a `*.cfgsync.bak` backup first unless `--no-backup` is provided.

When you run `cfgsync push`, the manifest and `items/` content are uploaded to the configured S3-compatible bucket. Cloudflare R2 works because it exposes an S3-compatible API.

## Install

From this checkout:

```bash
python3 -m pip install -e .
```

With Cloudflare R2/S3 support:

```bash
python3 -m pip install -e ".[s3]"
```

With `pipx`:

```bash
pipx install ".[s3]"
```

Homebrew:

```bash
brew tap alanzeng423/tap
brew install cfgsync
```

## Quick Start

Initialize a vault:

```bash
cfgsync init
```

Add common configs:

```bash
cfgsync add ghostty ~/.config/ghostty
cfgsync add codex ~/.codex
cfgsync add claude ~/.claude
cfgsync add hermes ~/.hermes
```

Review tracked entries:

```bash
cfgsync list
cfgsync status
```

Install symlinks from the vault back to each source path:

```bash
cfgsync install --dry-run
cfgsync install
```

## Cloudflare R2 Setup

Create a Cloudflare R2 bucket and an R2 API token with access to that bucket. Then configure the remote:

```bash
cfgsync remote set r2 \
  --bucket my-config-bucket \
  --prefix personal/macbook \
  --endpoint-url https://<account-id>.r2.cloudflarestorage.com \
  --region auto

export R2_ACCESS_KEY_ID="..."
export R2_SECRET_ACCESS_KEY="..."

cfgsync push
```

On another machine:

```bash
cfgsync init
cfgsync remote set r2 \
  --bucket my-config-bucket \
  --prefix personal/macbook \
  --endpoint-url https://<account-id>.r2.cloudflarestorage.com \
  --region auto

export R2_ACCESS_KEY_ID="..."
export R2_SECRET_ACCESS_KEY="..."

cfgsync pull
cfgsync install --dry-run
cfgsync install
```

The R2 endpoint format is:

```text
https://<account-id>.r2.cloudflarestorage.com
```

The `region` value can usually stay as `auto` for R2.

## Vault Layout

By default the vault lives at:

```text
~/.local/share/cfgsync
```

You can override it for one command:

```bash
cfgsync --vault /path/to/vault status
```

The vault contains:

```text
manifest.json       tracked paths, hashes, and remote settings
items/<name>/       copied config content
```

## Command Reference

### `cfgsync init`

Create the vault directory and an empty manifest if they do not already exist.

```bash
cfgsync init
```

### `cfgsync add <name> <path>`

Copy a config file or directory into the vault and track the original source path.

```bash
cfgsync add ghostty ~/.config/ghostty
cfgsync add codex ~/.codex
```

### `cfgsync list`

Show all tracked configs.

```bash
cfgsync list
```

### `cfgsync status`

Compare each original source path against the vaulted copy.

```bash
cfgsync status
```

Status values:

- `clean`: source and vault match.
- `changed`: source and vault differ.
- `source-missing`: the original source path is missing.
- `vault-missing`: the vaulted copy is missing.

### `cfgsync diff <name>`

Show a unified diff for a tracked file.

```bash
cfgsync diff ghostty
```

Directory diffs are not implemented yet.

### `cfgsync refresh [name]`

Copy source changes back into the vault. Without `name`, all tracked configs are refreshed.

```bash
cfgsync refresh ghostty
cfgsync refresh
```

### `cfgsync install`

Install vaulted configs back to their source paths as symlinks.

```bash
cfgsync install --dry-run
cfgsync install
cfgsync install --no-backup
```

### `cfgsync remote set`

Configure remote object storage metadata.

```bash
cfgsync remote set r2 \
  --bucket my-config-bucket \
  --prefix personal/macbook \
  --endpoint-url https://<account-id>.r2.cloudflarestorage.com \
  --region auto
```

### `cfgsync push`

Upload the local vault to the configured remote.

```bash
cfgsync push --dry-run
cfgsync push
```

### `cfgsync pull`

Download the remote vault into the local vault.

```bash
cfgsync pull --dry-run
cfgsync pull
```

## Automation

Run a dry status check from cron:

```cron
*/30 * * * * /opt/homebrew/bin/cfgsync status >/tmp/cfgsync-status.log 2>&1
```

Push periodically after local changes:

```cron
0 */6 * * * /opt/homebrew/bin/cfgsync push >/tmp/cfgsync-push.log 2>&1
```

For macOS launchd, use the example plist in [packaging/launchd/com.example.cfgsync.push.plist](packaging/launchd/com.example.cfgsync.push.plist).

## Safety Model

- `cfgsync install` backs up replaced source paths as `*.cfgsync.bak` by default.
- R2/S3 credentials are read from `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `AWS_ACCESS_KEY_ID`, or `AWS_SECRET_ACCESS_KEY`.
- Credentials are not written to `manifest.json`.
- The current release does not encrypt config content before upload.
- Use a private bucket and least-privilege R2 credentials.
- Do not sync raw secrets unless you are comfortable with your bucket security, or encrypt those files separately with tools such as age or SOPS.

## Packaging Notes

This project is packaged with `pyproject.toml` and exposes `cfgsync` through `project.scripts`.

Build a wheel:

```bash
python3 -m pip install build
python3 -m build
```

Install from the wheel:

```bash
python3 -m pip install dist/cfgsync-*.whl
```

Homebrew is published through:

```text
https://github.com/alanzeng423/homebrew-tap
```

Detailed PyPI and Homebrew release instructions are in [docs/publishing.md](docs/publishing.md).

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m cfgsync.cli --help
```

## Roadmap

- Directory-level diff output.
- Optional client-side encryption before remote upload.
- Conflict detection for remote pull.
- Machine profiles for different laptops or servers.
- Native Homebrew tap release workflow.
- Optional Git-backed local history in the vault.
