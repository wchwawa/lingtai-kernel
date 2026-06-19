"""Built-in tool registry.

The four always-present tools live with the rest of the tool implementations under
``lingtai.core.<tool>``.  This kernel registry records their module paths without
importing them, so ``import lingtai.kernel`` / ``import lingtai_sdk`` stays
import-light; the modules are imported only when an agent is actually wiring or
rendering its tool surface.
"""
from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from types import ModuleType

BUILTIN_TOOL_MODULES: dict[str, str] = {
    "email": "lingtai.core.email",
    "system": "lingtai.core.system",
    "psyche": "lingtai.core.psyche",
    "soul": "lingtai.core.soul",
}

BUILTIN_TOOL_NAMES: tuple[str, ...] = tuple(BUILTIN_TOOL_MODULES)


@lru_cache(maxsize=None)
def get_builtin_tool_module(name: str) -> ModuleType:
    """Import and return the canonical module for built-in tool *name*."""
    try:
        module_path = BUILTIN_TOOL_MODULES[name]
    except KeyError as exc:  # pragma: no cover - defensive API guard
        raise KeyError(f"unknown built-in tool: {name}") from exc
    return import_module(module_path)


__all__ = ["BUILTIN_TOOL_MODULES", "BUILTIN_TOOL_NAMES", "get_builtin_tool_module"]
