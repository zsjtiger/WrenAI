"""Deploy providers — interchangeable adapters behind the DeployProvider protocol."""

from __future__ import annotations

from janus.creport.providers.base import DeployProvider


def get_provider(name: str) -> DeployProvider:
    """Return the adapter for ``name`` or raise KeyError with the known set."""
    from janus.creport.providers.cloudflare import CloudflareProvider  # noqa: PLC0415
    from janus.creport.providers.ssh import SshProvider  # noqa: PLC0415
    from janus.creport.providers.vercel import VercelProvider  # noqa: PLC0415

    registry: dict[str, type] = {
        "vercel": VercelProvider,
        "cloudflare": CloudflareProvider,
        "ssh": SshProvider,
    }
    if name not in registry:
        raise KeyError(
            f"unknown provider {name!r}; expected one of: {', '.join(registry)}"
        )
    return registry[name]()
