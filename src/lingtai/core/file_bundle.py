"""Wrapper-side bridge: host the real ``read`` / ``glob`` / ``grep`` handlers
through the SDK file-tool bundle declarations (stage 3A).

This is the wrapper half of the SDK file-tool bundle template. The SDK module
:mod:`lingtai_sdk.file_tools` *declares* the three low-state file tools as
:class:`~lingtai_sdk.capabilities.BundleManifest` objects and offers a host
injection seam (``file_tool_hosts``), but — to respect the import boundary (the
SDK must not import the wrapper, and the kernel must not import the SDK) — it
ships **no real handler**. This module is where the wrapper, which *may* import
the SDK, injects the genuine file-tool handlers and so proves the
bundle-execution pattern end to end against the real behavior.

The handlers are the *same* closures the normal capability path registers:
``lingtai.core.{read,glob,grep}.make_handler(agent)``. There is no second
implementation — the bundle-hosted tool runs byte-identical logic to the tool
``setup()`` registers on the agent, against the same ``agent._file_io`` /
``agent._working_dir`` and the same path-sandbox / traversal-budget / error
semantics.

The wrapper handlers take a single ``args: dict``; the SDK
:class:`~lingtai_sdk.capability_host.BundleHost.invoke` passes keyword args. The
tiny ``_kwargs_adapter`` reconciles the two without changing either contract.

This module does **not** change how ``Agent`` registers or dispatches the file
tools — ``setup()`` remains the live path. It is an additive, observable seam:
a host (or a test) can drive the real file tools through the declared manifest,
which is the migration template later stages build on. Nothing here runs at
``Agent`` construction time.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from lingtai_kernel.base_agent import BaseAgent
    from lingtai_sdk.capability_host import BundleHost

# The wrapper's real handler factories — the single source of truth for each
# file tool's behavior, shared with the capability ``setup()`` path.
from . import glob as _glob
from . import grep as _grep
from . import read as _read

# name -> the module exposing ``make_handler(agent)`` for that file tool.
_HANDLER_FACTORIES: dict[str, Callable[["BaseAgent"], Callable[[dict], Any]]] = {
    "read": _read.make_handler,
    "glob": _glob.make_handler,
    "grep": _grep.make_handler,
}


def _kwargs_adapter(
    handler: Callable[[dict], Any],
) -> Callable[..., Any]:
    """Adapt an ``args: dict`` wrapper handler to ``BundleHost.invoke``'s kwargs.

    ``BundleHost.invoke(tool, **kwargs)`` calls its handler with keyword args,
    but the wrapper file-tool handlers take a single positional ``args`` dict.
    This collects the kwargs back into that dict so the real handler runs
    unchanged.
    """

    def _adapted(**kwargs: Any) -> Any:
        return handler(dict(kwargs))

    return _adapted


def file_tool_handlers(agent: "BaseAgent") -> dict[str, Callable[..., Any]]:
    """Build the ``{name: kwargs-handler}`` mapping the SDK host seam expects.

    Each handler is the wrapper's real ``make_handler(agent)`` closure, adapted
    to the host's keyword-args invocation contract. Bound to *agent*, so it reads
    through ``agent._file_io`` / ``agent._working_dir`` exactly as the registered
    tool does.
    """
    return {
        name: _kwargs_adapter(factory(agent))
        for name, factory in _HANDLER_FACTORIES.items()
    }


def file_tool_bundle_hosts(agent: "BaseAgent") -> dict[str, "BundleHost"]:
    """Host the real file tools through the SDK file-tool bundle declarations.

    Returns ``{name: BundleHost}`` for ``read`` / ``glob`` / ``grep``, each
    hosting the bundle's one declared tool with the wrapper's genuine handler
    (bound to *agent*). The SDK is imported here, in the wrapper, not at SDK
    module load — preserving the one-way ``wrapper -> sdk`` direction.

    ``host.invoke(name, **args)`` then runs the real file-tool logic through the
    declared manifest, proving the bundle-execution pattern against actual
    behavior. This does not alter the agent's live tool registration.
    """
    from lingtai_sdk.file_tools import file_tool_hosts

    return file_tool_hosts(file_tool_handlers(agent))


__all__ = [
    "file_tool_handlers",
    "file_tool_bundle_hosts",
]
