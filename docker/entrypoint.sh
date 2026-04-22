#!/bin/bash
# Docker/Podman entrypoint: bootstrap config files into the mounted volume, then run hermes.
set -e

HERMES_HOME="${HERMES_HOME:-/opt/data}"
INSTALL_DIR="/opt/hermes"
CLONE_MARKER="$HERMES_HOME/.clone_initialized"

# --- Privilege dropping via gosu ---
# When started as root (the default for Docker, or fakeroot in rootless Podman),
# optionally remap the hermes user/group to match host-side ownership, fix volume
# permissions, then re-exec as hermes.
if [ "$(id -u)" = "0" ]; then
    if [ -n "$HERMES_UID" ] && [ "$HERMES_UID" != "$(id -u hermes)" ]; then
        echo "Changing hermes UID to $HERMES_UID"
        usermod -u "$HERMES_UID" hermes
    fi

    if [ -n "$HERMES_GID" ] && [ "$HERMES_GID" != "$(id -g hermes)" ]; then
        echo "Changing hermes GID to $HERMES_GID"
        # -o allows non-unique GID (e.g. macOS GID 20 "staff" may already exist
        # as "dialout" in the Debian-based container image)
        groupmod -o -g "$HERMES_GID" hermes 2>/dev/null || true
    fi

    actual_hermes_uid=$(id -u hermes)
    if [ "$(stat -c %u "$HERMES_HOME" 2>/dev/null)" != "$actual_hermes_uid" ]; then
        echo "$HERMES_HOME is not owned by $actual_hermes_uid, fixing"
        # In rootless Podman the container's "root" is mapped to an unprivileged
        # host UID — chown will fail.  That's fine: the volume is already owned
        # by the mapped user on the host side.
        chown -R hermes:hermes "$HERMES_HOME" 2>/dev/null || \
            echo "Warning: chown failed (rootless container?) — continuing anyway"
    fi

    echo "Dropping root privileges"
    exec gosu hermes "$0" "$@"
fi

# --- Running as hermes from here ---
source "${INSTALL_DIR}/.venv/bin/activate"
# Always use the venv interpreter for repo scripts. In some container/gosu
# contexts `python3` can still resolve to the system binary (no deps), which
# makes skills_sync and other boot steps fail with set -e and exits the whole
# process before the gateway starts.
VENV_PY="${INSTALL_DIR}/.venv/bin/python"

# Create essential directory structure.  Cache and platform directories
# (cache/images, cache/audio, platforms/whatsapp, etc.) are created on
# demand by the application — don't pre-create them here so new installs
# get the consolidated layout from get_hermes_dir().
# The "home/" subdirectory is a per-profile HOME for subprocesses (git,
# ssh, gh, npm …).  Without it those tools write to /root which is
# ephemeral and shared across profiles.  See issue #4426.
mkdir -p "$HERMES_HOME"/{cron,sessions,logs,hooks,memories,skills,skins,plans,workspace,home}

# Clone bootstrap behavior:
# - fresh (default): ensure no historical session DB/files are carried over
# - stateful: optional tarball restore from HERMES_CLONE_SNAPSHOT_URL (one-time)
CLONE_MODE="${HERMES_CLONE_MODE:-fresh}"
if [ ! -f "$CLONE_MARKER" ]; then
    if [ "$CLONE_MODE" = "stateful" ] && [ -n "${HERMES_CLONE_SNAPSHOT_URL:-}" ]; then
        tmp_snapshot="/tmp/hermes_clone_snapshot.tgz"
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL "$HERMES_CLONE_SNAPSHOT_URL" -o "$tmp_snapshot"
            tar -xzf "$tmp_snapshot" -C "$HERMES_HOME"
            rm -f "$tmp_snapshot"
        fi
    else
        # Fresh clone: remove prior chat/session artifacts if any exist.
        rm -f "$HERMES_HOME/state.db" "$HERMES_HOME/state.db-shm" "$HERMES_HOME/state.db-wal"
        rm -f "$HERMES_HOME/response_store.db" "$HERMES_HOME/response_store.db-shm" "$HERMES_HOME/response_store.db-wal"
        rm -rf "$HERMES_HOME/sessions/"*
    fi
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$CLONE_MARKER"
fi

# .env
if [ ! -f "$HERMES_HOME/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$HERMES_HOME/.env"
fi

# config.yaml
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
    cp "$INSTALL_DIR/cli-config.yaml.example" "$HERMES_HOME/config.yaml"
fi

# SOUL.md
if [ ! -f "$HERMES_HOME/SOUL.md" ]; then
    cp "$INSTALL_DIR/docker/SOUL.md" "$HERMES_HOME/SOUL.md"
fi

# Sync bundled skills (manifest-based so user edits are preserved)
if [ -d "$INSTALL_DIR/skills" ]; then
    "$VENV_PY" "$INSTALL_DIR/tools/skills_sync.py"
fi

# Optional standalone controller mode for dedicated control-plane services.
# Keeps the default Hermes behavior unchanged unless explicitly enabled.
if [ "${HERMES_RUN_MODE:-}" = "controller" ]; then
    exec "$VENV_PY" -m controller.main
fi

exec hermes "$@"
