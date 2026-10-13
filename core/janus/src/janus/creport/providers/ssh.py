"""SSH static-site adapter — publishes a CReport build to a server you control.

The build is packed into a tarball and streamed over ``ssh`` into a new
release directory, then a ``current`` symlink is switched to it atomically.
A web server (nginx, Caddy, ...) serving ``<root>/<app>/current`` therefore
never sees a half-written site. Needs only ``ssh`` on PATH and key-based
access to the host; no vendor token is involved.

Configuration comes from the environment only (nothing is written to disk):

  CREPORT_SSH_HOST   server hostname or IP                      (required)
  CREPORT_SSH_DIR    absolute remote root, e.g. /var/www/creport (required)
  CREPORT_SSH_URL    public base URL the site is served at       (required)
  CREPORT_SSH_USER   remote user                                 (optional)
  CREPORT_SSH_PORT   remote port                                 (optional)
  CREPORT_SSH_KEY    private key file passed to ssh -i           (optional)

Layout on the server:

  <root>/<app>/releases/<release-id>/...   one directory per deploy
  <root>/<app>/current -> releases/<release-id>

Old releases are kept; remove them by hand when disk space matters.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from janus.creport.providers.base import DeployError, Deployment

_APP_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_HOST_RE = re.compile(r"^[A-Za-z0-9._@:-]+$")
_PORT_RE = re.compile(r"^[0-9]{1,5}$")


def _config() -> dict:
    env = os.environ
    host = env.get("CREPORT_SSH_HOST", "").strip()
    root = env.get("CREPORT_SSH_DIR", "").strip()
    base = env.get("CREPORT_SSH_URL", "").strip().rstrip("/")
    missing = [
        name
        for name, value in (
            ("CREPORT_SSH_HOST", host),
            ("CREPORT_SSH_DIR", root),
            ("CREPORT_SSH_URL", base),
        )
        if not value
    ]
    if missing:
        raise DeployError(
            "missing "
            + ", ".join(missing)
            + " — set them before deploying with --provider ssh"
        )
    if not _HOST_RE.match(host):
        raise DeployError(f"CREPORT_SSH_HOST has unsupported characters: {host!r}")
    if not root.startswith("/"):
        raise DeployError(
            f"CREPORT_SSH_DIR must be an absolute path on the server, got {root!r}"
        )
    if not base.startswith(("http://", "https://")):
        raise DeployError(
            f"CREPORT_SSH_URL must start with http:// or https://, got {base!r}"
        )

    user = env.get("CREPORT_SSH_USER", "").strip()
    port = env.get("CREPORT_SSH_PORT", "").strip()
    key = env.get("CREPORT_SSH_KEY", "").strip()
    if user and not _HOST_RE.match(user):
        raise DeployError(f"CREPORT_SSH_USER has unsupported characters: {user!r}")
    if port and not _PORT_RE.match(port):
        raise DeployError(f"CREPORT_SSH_PORT must be a number, got {port!r}")
    return {
        "host": host,
        "root": root.rstrip("/") or "/",
        "base": base,
        "user": user,
        "port": port,
        "key": key,
    }


def _release_id(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{os.urandom(3).hex()}"


def _pack(build_dir: Path, dest: Path) -> None:
    with tarfile.open(dest, "w:gz") as tar:
        for path in sorted(build_dir.rglob("*")):
            if path.is_file():
                tar.add(
                    path,
                    arcname=path.relative_to(build_dir).as_posix(),
                    recursive=False,
                )


def _remote_script(site_dir: str, release_id: str) -> str:
    """Shell run on the server: unpack stdin into a new release, then swap ``current``."""
    release = f"{site_dir}/releases/{release_id}"
    current = f"{site_dir}/current"
    staging = f"{current}.new"
    return " && ".join(
        [
            f"mkdir -p {shlex.quote(release)}",
            f"tar -xzf - -C {shlex.quote(release)}",
            f"ln -sfn {shlex.quote(release)} {shlex.quote(staging)}",
            f"mv -Tf {shlex.quote(staging)} {shlex.quote(current)}",
        ]
    )


def _ssh_argv(cfg: dict, remote_cmd: str) -> list[str]:
    argv = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
    if cfg["port"]:
        argv += ["-p", cfg["port"]]
    if cfg["key"]:
        argv += ["-i", cfg["key"]]
    target = f"{cfg['user']}@{cfg['host']}" if cfg["user"] else cfg["host"]
    return [*argv, target, remote_cmd]


def _run(argv: list[str], data: bytes) -> subprocess.CompletedProcess:
    """Run ssh with the tarball on stdin. Patched in tests."""
    return subprocess.run(argv, input=data, capture_output=True, timeout=600)


class SshProvider:
    name = "ssh"
    # No vendor token: access is governed by the SSH key / agent.
    env_token_var = None

    def deploy(
        self,
        build_dir: Path,
        *,
        app_name: str,
        token: str,  # noqa: ARG002 — unused; SSH authenticates with keys
        prod: bool,  # noqa: ARG002 — one live location, so prod and preview are the same
        link: dict | None,  # noqa: ARG002 — no provider state to persist
    ) -> Deployment:
        if not _APP_RE.match(app_name):
            raise DeployError(
                f"app name {app_name!r} is not usable as a directory name "
                "(lowercase letters, digits, '-' and '_')"
            )
        cfg = _config()
        if not build_dir.is_dir():
            raise DeployError(f"build directory not found: {build_dir}")

        site_dir = f"{cfg['root']}/{app_name}"
        release_id = _release_id()
        with tempfile.TemporaryDirectory() as tmp:
            tarball = Path(tmp) / "site.tar.gz"
            _pack(build_dir, tarball)
            data = tarball.read_bytes()

        argv = _ssh_argv(cfg, _remote_script(site_dir, release_id))
        result = _run(argv, data)
        if result.returncode != 0:
            detail = (
                (result.stderr or result.stdout or b"")
                .decode("utf-8", "replace")
                .strip()
            )
            raise DeployError(
                f"upload to {cfg['host']} failed: {detail or 'ssh exited non-zero'}"
            )

        return Deployment(url=f"{cfg['base']}/{app_name}/", environment="production")
