"""Behaviour tests for the SSH static-site provider (`--provider ssh`).

The server side is exercised for real: the remote shell script is executed
with ``sh`` against a temporary directory standing in for the server root, so
the release/symlink logic is tested rather than its string form.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import janus.creport.providers.ssh as ssh
from janus.cli import app
from janus.creport.providers import get_provider
from janus.creport.providers.base import DeployError

runner = CliRunner()

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_ssh_env(monkeypatch):
    for name in (
        "CREPORT_SSH_HOST",
        "CREPORT_SSH_DIR",
        "CREPORT_SSH_URL",
        "CREPORT_SSH_USER",
        "CREPORT_SSH_PORT",
        "CREPORT_SSH_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def _build(tmp_path: Path, text: str = "<html>v1</html>") -> Path:
    build = tmp_path / "build"
    (build / "data").mkdir(parents=True)
    (build / "index.html").write_text(text)
    (build / "mdl.json").write_text(json.dumps({"models": []}))
    (build / "data" / "orders.parquet").write_bytes(b"PAR1fake")
    return build


def _configure(monkeypatch, root: Path, **extra: str) -> None:
    monkeypatch.setenv("CREPORT_SSH_HOST", "static.example.test")
    monkeypatch.setenv("CREPORT_SSH_DIR", str(root))
    monkeypatch.setenv("CREPORT_SSH_URL", "https://apps.example.test")
    for name, value in extra.items():
        monkeypatch.setenv(name, value)


def _run_remote_locally(argv: list[str], data: bytes) -> subprocess.CompletedProcess:
    """Stand-in for ssh: execute the remote command in a local shell."""
    return subprocess.run(["sh", "-c", argv[-1]], input=data, capture_output=True)


# ── registry and token contract ───────────────────────────────────────────────


def test_ssh_is_registered_and_needs_no_vendor_token() -> None:
    adapter = get_provider("ssh")
    assert adapter.name == "ssh"
    assert adapter.env_token_var is None


# ── configuration ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "missing", ["CREPORT_SSH_HOST", "CREPORT_SSH_DIR", "CREPORT_SSH_URL"]
)
def test_missing_required_setting_is_named(tmp_path, monkeypatch, missing) -> None:
    _configure(monkeypatch, tmp_path)
    monkeypatch.delenv(missing)
    with pytest.raises(DeployError, match=missing):
        get_provider("ssh").deploy(
            _build(tmp_path), app_name="myapp", token="", prod=True, link=None
        )


def test_relative_remote_dir_is_refused(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv("CREPORT_SSH_DIR", "var/www/creport")
    with pytest.raises(DeployError, match="absolute path"):
        get_provider("ssh").deploy(
            _build(tmp_path), app_name="myapp", token="", prod=True, link=None
        )


def test_url_without_scheme_is_refused(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv("CREPORT_SSH_URL", "apps.example.test")
    with pytest.raises(DeployError, match="http"):
        get_provider("ssh").deploy(
            _build(tmp_path), app_name="myapp", token="", prod=True, link=None
        )


def test_non_numeric_port_is_refused(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path, CREPORT_SSH_PORT="22; rm -rf /")
    with pytest.raises(DeployError, match="PORT"):
        get_provider("ssh").deploy(
            _build(tmp_path), app_name="myapp", token="", prod=True, link=None
        )


def test_host_that_looks_like_an_option_is_refused(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv("CREPORT_SSH_HOST", "-oProxyCommand=evil")
    with pytest.raises(DeployError, match="HOST"):
        get_provider("ssh").deploy(
            _build(tmp_path), app_name="myapp", token="", prod=True, link=None
        )


@pytest.mark.parametrize("bad", ["../escape", "My App", "a/b", ""])
def test_app_name_must_be_a_safe_directory_name(tmp_path, monkeypatch, bad) -> None:
    _configure(monkeypatch, tmp_path)
    with pytest.raises(DeployError, match="directory name"):
        get_provider("ssh").deploy(
            _build(tmp_path), app_name=bad, token="", prod=True, link=None
        )


# ── ssh invocation ────────────────────────────────────────────────────────────


def test_ssh_command_uses_key_port_and_user_without_a_shell(
    tmp_path, monkeypatch
) -> None:
    _configure(
        monkeypatch,
        tmp_path,
        CREPORT_SSH_USER="deploy",
        CREPORT_SSH_PORT="2222",
        CREPORT_SSH_KEY="/keys/creport",
    )
    seen: list[list[str]] = []

    def fake_run(argv, data):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(ssh, "_run", fake_run)
    get_provider("ssh").deploy(
        _build(tmp_path), app_name="myapp", token="", prod=True, link=None
    )

    argv = seen[0]
    assert argv[0] == "ssh"
    assert "BatchMode=yes" in argv
    assert argv[argv.index("-p") + 1] == "2222"
    assert argv[argv.index("-i") + 1] == "/keys/creport"
    assert "deploy@static.example.test" in argv
    # the remote command is one argv element, never interpolated into a local shell
    assert argv[-1].startswith("mkdir -p ")


def test_upload_payload_is_a_gzipped_tar_of_the_build(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)
    captured: dict[str, bytes] = {}

    def fake_run(argv, data):
        captured["data"] = data
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(ssh, "_run", fake_run)
    get_provider("ssh").deploy(
        _build(tmp_path), app_name="myapp", token="", prod=True, link=None
    )
    with tarfile.open(fileobj=io.BytesIO(captured["data"]), mode="r:gz") as tar:
        names = set(tar.getnames())
    assert {"index.html", "mdl.json", "data/orders.parquet"} <= names


def test_ssh_failure_surfaces_stderr(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)

    def failing(argv, data):
        return subprocess.CompletedProcess(
            argv, 255, b"", b"Permission denied (publickey)."
        )

    monkeypatch.setattr(ssh, "_run", failing)
    with pytest.raises(DeployError, match="Permission denied"):
        get_provider("ssh").deploy(
            _build(tmp_path), app_name="myapp", token="", prod=True, link=None
        )


# ── server side, executed for real ────────────────────────────────────────────


def test_two_deploys_switch_current_and_keep_old_releases(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / "server" / "creport"
    _configure(monkeypatch, root)
    monkeypatch.setattr(ssh, "_run", _run_remote_locally)
    adapter = get_provider("ssh")

    first = adapter.deploy(
        _build(tmp_path / "a", "<html>v1</html>"),
        app_name="myapp",
        token="",
        prod=True,
        link=None,
    )
    second = adapter.deploy(
        _build(tmp_path / "b", "<html>v2</html>"),
        app_name="myapp",
        token="",
        prod=True,
        link=None,
    )

    site = root / "myapp"
    assert (site / "current" / "index.html").read_text() == "<html>v2</html>"
    assert (site / "current" / "data" / "orders.parquet").read_bytes() == b"PAR1fake"
    releases = sorted(p.name for p in (site / "releases").iterdir())
    assert len(releases) == 2, "old release must be kept"
    assert not (site / "current.new").exists(), "staging link must not be left behind"
    assert first.url == second.url == "https://apps.example.test/myapp/"


def test_remote_script_quotes_paths_with_spaces(tmp_path, monkeypatch) -> None:
    root = tmp_path / "with space" / "creport"
    _configure(monkeypatch, root)
    monkeypatch.setattr(ssh, "_run", _run_remote_locally)
    get_provider("ssh").deploy(
        _build(tmp_path), app_name="myapp", token="", prod=True, link=None
    )
    assert (root / "myapp" / "current" / "index.html").exists()


def test_failed_unpack_leaves_current_untouched(tmp_path, monkeypatch) -> None:
    root = tmp_path / "creport"
    _configure(monkeypatch, root)
    monkeypatch.setattr(ssh, "_run", _run_remote_locally)
    adapter = get_provider("ssh")
    adapter.deploy(
        _build(tmp_path / "a", "<html>good</html>"),
        app_name="myapp",
        token="",
        prod=True,
        link=None,
    )

    def corrupt_upload(argv, data):
        return _run_remote_locally(argv, b"not a tarball")

    monkeypatch.setattr(ssh, "_run", corrupt_upload)
    with pytest.raises(DeployError):
        adapter.deploy(
            _build(tmp_path / "b", "<html>bad</html>"),
            app_name="myapp",
            token="",
            prod=True,
            link=None,
        )
    assert (
        root / "myapp" / "current" / "index.html"
    ).read_text() == "<html>good</html>"


# ── CLI: deploy with no vendor token ──────────────────────────────────────────


def _deployable_project(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "janus_project.yml").write_text(
        'schema_version: 2\nname: test_proj\nversion: "1.0"\n'
        "catalog: janus\nschema: public\ndata_source: duckdb\n"
    )
    app_dir = tmp_path / "apps" / "myapp"
    (app_dir / "data").mkdir(parents=True)
    (app_dir / "index.html").write_text("<html><body>CReport</body></html>")
    (app_dir / "mdl.json").write_text(json.dumps({"models": [{}]}))
    (app_dir / "data" / "orders.parquet").write_bytes(b"PAR1fake")
    result = runner.invoke(app, ["creport", "register", "myapp", "-p", str(tmp_path)])
    assert result.exit_code == 0, result.output
    return tmp_path


def test_cli_deploy_over_ssh_needs_no_token_and_persists_state(
    tmp_path, monkeypatch
) -> None:
    project = _deployable_project(tmp_path / "proj")
    root = tmp_path / "server" / "creport"
    _configure(monkeypatch, root)
    monkeypatch.setattr(ssh, "_run", _run_remote_locally)

    result = runner.invoke(
        app,
        [
            "creport",
            "deploy",
            "myapp",
            "--provider",
            "ssh",
            "--prod",
            "-p",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "https://apps.example.test/myapp/" in result.output
    assert (root / "myapp" / "current" / "index.html").exists()
    index = yaml.safe_load((project / ".janus" / "apps.yml").read_text())
    deploy = index["apps"]["myapp"]["deploy"]
    assert deploy["provider"] == "ssh"
    assert deploy["last_url"] == "https://apps.example.test/myapp/"
    assert deploy["environment"] == "production"
