"""Resolve per-workspace app, agent, and ontology seed lists from Nexus settings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from naas_abi.apps.nexus.apps.api.app.core import config as nexus_config


def live_settings() -> Any:
    """Return the live Settings object.

    ``on_initialized`` replaces ``nexus_config.settings``. Callers must not
    bind the import-time snapshot.
    """
    return nexus_config.settings


def workspace_seed_for_slug(slug: str | None) -> Any | None:
    if not slug:
        return None
    for org in getattr(live_settings(), "organizations", None) or []:
        for workspace in getattr(org, "workspaces", None) or []:
            if workspace.slug == slug:
                return workspace
    return None


def parse_agent_ref(raw: str) -> tuple[str, str] | None:
    """Split ``module AgentClass`` (same form as engine ``default_agent``)."""
    text = (raw or "").strip()
    if " " not in text:
        return None
    module_name, agent_name = text.split(" ", 1)
    module_name = module_name.strip()
    agent_name = agent_name.strip()
    if not module_name or not agent_name:
        return None
    return module_name, agent_name


def resolve_agent_ref(raw: str, registry: Mapping[str, Any]) -> str | None:
    """Return the registry key for ``module AgentClass``, or None."""
    parsed = parse_agent_ref(raw)
    if parsed is None:
        return None
    module_name, agent_name = parsed
    suffix = f"/{agent_name}"
    for class_name in registry:
        if not class_name.endswith(suffix):
            continue
        if class_name == f"{module_name}/{agent_name}" or class_name.startswith(
            f"{module_name}."
        ):
            return class_name
    matches = [key for key in registry if key.endswith(suffix)]
    if len(matches) == 1:
        return matches[0]
    return None


def resolve_agent_refs(refs: list[str] | None, registry: Mapping[str, Any]) -> set[str]:
    resolved: set[str] = set()
    for raw in refs or []:
        class_name = resolve_agent_ref(raw, registry)
        if class_name:
            resolved.add(class_name)
    return resolved


def resolve_app_enabled(
    app_id: str,
    enabled_by_app_id: Mapping[str, bool],
    seed_apps: set[str],
) -> bool:
    """DB row wins; otherwise the seed list; otherwise off."""
    if app_id in enabled_by_app_id:
        return enabled_by_app_id[app_id]
    return app_id in seed_apps


def parse_ontology_ref(raw: str) -> tuple[str | None, str] | None:
    """Split ``module OntologyName``, ``module:OntologyName``, or a bare name/path.

    Same roster form as ``agents:`` (space) and ``apps:`` (colon). A bare
    filename, stem, or path suffix is also accepted.
    """
    text = (raw or "").strip()
    if not text:
        return None
    if ":" in text and "://" not in text and not text.startswith("/"):
        module_name, ontology_name = text.split(":", 1)
        module_name = module_name.strip()
        ontology_name = ontology_name.strip()
        if module_name and ontology_name:
            return module_name, ontology_name
        return None
    if " " in text:
        module_name, ontology_name = text.split(" ", 1)
        module_name = module_name.strip()
        ontology_name = ontology_name.strip()
        if module_name and ontology_name:
            return module_name, ontology_name
        return None
    return None, text


def _norm(value: str) -> str:
    return value.strip().lower().replace("_", " ").replace("-", " ")


def _ontology_module_matches(module_ref: str, item: Any) -> bool:
    needle = _norm(module_ref).replace(" ", "")
    if not needle:
        return False
    module_name = _norm(str(getattr(item, "module_name", "") or "")).replace(" ", "")
    if module_name and (
        module_name == needle or module_name.endswith(needle) or needle.endswith(module_name)
    ):
        return True
    path = str(getattr(item, "path", "") or "").replace("\\", "/").lower()
    token = module_ref.strip().lower().replace(" ", "_")
    return f"/{token}/" in f"/{path}/" or f"/{token}." in f"/{path}"


def _ontology_name_matches(name_ref: str, item: Any) -> bool:
    raw = name_ref.strip()
    if not raw:
        return False
    path = str(getattr(item, "path", "") or "").replace("\\", "/")
    filename = path.rsplit("/", 1)[-1] if path else ""
    stem = filename.rsplit(".", 1)[0] if filename else ""
    title = str(getattr(item, "name", "") or "")
    lowered = raw.lower()
    if path == raw or path.endswith(f"/{raw}") or path.lower().endswith(lowered):
        return True
    if filename.lower() == lowered or stem.lower() == lowered:
        return True
    return _norm(title) == _norm(raw) or _norm(stem) == _norm(raw)


def ontology_ref_matches(raw: str, item: Any) -> bool:
    """Return True when *item* is the catalog entry named by *raw*."""
    parsed = parse_ontology_ref(raw)
    if parsed is None:
        return False
    module_name, ontology_name = parsed
    if not _ontology_name_matches(ontology_name, item):
        return False
    if module_name is None:
        return True
    return _ontology_module_matches(module_name, item)


def filter_ontology_files(items: list[Any], refs: list[str] | None) -> list[Any]:
    """Keep catalog rows that match ``ontologies:``. ``None`` means no filter."""
    if refs is None:
        return list(items)
    wanted = [str(ref).strip() for ref in refs if str(ref).strip()]
    if not wanted:
        return []
    return [item for item in items if any(ontology_ref_matches(ref, item) for ref in wanted)]
