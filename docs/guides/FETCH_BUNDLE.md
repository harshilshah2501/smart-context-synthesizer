# Fetch toolkit bundle from build server (WSL ← Linux dev machine)

Use when your **build server** has the repo and WSL is your daily dev box. Replaces manual SharePoint download for solo/dev sync.

---

## Architecture

```text
Build server (SSH)                    WSL (DESKTOP-MBPAQK1)
/home/harshil/.../packaging/build/    /root/Harshil-PoCs/
  context-synthesizer-toolkit-latest.tar.gz  ←── rsync (cron)
  context-synthesizer-toolkit-latest/          ←── auto-extract
```

On the build server, `build-release-tarball.sh` creates a **`context-synthesizer-toolkit-latest.tar.gz`** symlink to the newest dated tarball.

---

## One-time setup (WSL)

### 1. SSH key (passwordless)

On WSL:

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519_build 2>/dev/null || true
ssh-copy-id -i ~/.ssh/id_ed25519_build harshil@YOUR_BUILD_SERVER
ssh harshil@YOUR_BUILD_SERVER "echo OK"
```

Replace `YOUR_BUILD_SERVER` with hostname or IP (e.g. `pro6000-server`, `192.168.1.50`).

Optional `~/.ssh/config`:

```sshconfig
Host build-server
  HostName 192.168.1.50
  User harshil
  IdentityFile ~/.ssh/id_ed25519_build
```

Then use `BUILD_HOST="build-server"` in config below.

### 2. Config

```bash
mkdir -p ~/.config/context-synthesizer

cat > ~/.config/context-synthesizer/bundle-sync.env <<'EOF'
BUILD_HOST="harshil@YOUR_BUILD_SERVER"
REMOTE_TARBALL="/home/harshil/Out-of-bound-chronicles/context-synthesizer/packaging/build/context-synthesizer-toolkit-latest.tar.gz"
LOCAL_DIR="/root/Harshil-PoCs"
EXTRACT=1
PRUNE_OLD=1
CRON_SCHEDULE="0 */2 * * *"
EOF
```

### 3. Fetch script

Copy from repo (or use path inside synced toolkit):

```bash
chmod +x /path/to/fetch-toolkit-bundle.sh
bash /path/to/fetch-toolkit-bundle.sh
```

Result:

```text
/root/Harshil-PoCs/context-synthesizer-toolkit-latest.tar.gz
/root/Harshil-PoCs/context-synthesizer-toolkit-latest/   ← extracted, ready for run-setup.sh
```

---

## Background sync (cron)

Every 2 hours (edit `CRON_SCHEDULE` in `bundle-sync.env`):

```bash
bash context-synthesizer/packaging/fetch-toolkit-bundle.sh --install-cron
```

Log: `~/.local/state/context-synthesizer/bundle-sync.log`

Verify:

```bash
crontab -l
tail -f ~/.local/state/context-synthesizer/bundle-sync.log
```

Remove cron:

```bash
crontab -l | grep -v fetch-toolkit-bundle | crontab -
```

---

## Build server (after each release)

```bash
cd /home/harshil/Out-of-bound-chronicles
bash context-synthesizer/packaging/build-release-tarball.sh
# Creates .../context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
# Symlink: .../context-synthesizer-toolkit-latest.tar.gz
```

WSL cron picks up `latest` on next rsync.

---

## Manual one-shot rsync (no script)

```bash
rsync -avz --partial \
  harshil@YOUR_BUILD_SERVER:/home/harshil/Out-of-bound-chronicles/context-synthesizer/packaging/build/context-synthesizer-toolkit-latest.tar.gz \
  /root/Harshil-PoCs/

cd /root/Harshil-PoCs
tar -xzf context-synthesizer-toolkit-latest.tar.gz
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Permission denied (publickey)` | Run `ssh-copy-id`; test `ssh BUILD_HOST` |
| `No such file` on remote | Run `build-release-tarball.sh` on server first |
| WSL cron not running | `sudo service cron start` (WSL) |
| Firewall | Allow SSH (22) from WSL IP to build server |

See also [DEPLOY.md](DEPLOY.md) · [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)
