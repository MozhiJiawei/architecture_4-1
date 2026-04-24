from __future__ import annotations

from typing import Any


def validate_logic_view(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(model.get("view") or "").strip().lower() != "logic":
        errors.append("Logic validator only accepts view='logic'.")

    groups = [item for item in (model.get("groups") or []) if isinstance(item, dict)]
    elements = [item for item in (model.get("elements") or []) if isinstance(item, dict)]
    relationships = [item for item in (model.get("relationships") or []) if isinstance(item, dict)]
    if not groups:
        errors.append("Logic view must include at least one group.")
    if not elements:
        errors.append("Logic view must include at least one element.")

    group_ids = {str(group.get("id") or "") for group in groups if str(group.get("id") or "")}
    element_ids = {str(element.get("id") or "") for element in elements if str(element.get("id") or "")}
    if len(group_ids) != len([group for group in groups if str(group.get("id") or "")]):
        errors.append("Logic view contains duplicate group ids.")
    if len(element_ids) != len([element for element in elements if str(element.get("id") or "")]):
        errors.append("Logic view contains duplicate element ids.")
    for element in elements:
        element_id = str(element.get("id") or "")
        if not element_id:
            errors.append("Logic element is missing id.")
        group_id = str(element.get("group") or "")
        if group_id and group_id not in group_ids:
            errors.append(f"Logic element {element_id} references unknown group {group_id}.")

    seen_relationships: set[tuple[str, str, str, str]] = set()
    for relationship in relationships:
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        kind = str(relationship.get("kind") or "")
        label = str(relationship.get("label") or "")
        if source not in element_ids:
            errors.append(f"Logic relationship references unknown source {source}.")
        if target not in element_ids:
            errors.append(f"Logic relationship references unknown target {target}.")
        signature = (source, target, kind, label)
        if signature in seen_relationships:
            errors.append(f"Duplicate logic relationship {source} -> {target} ({kind} / {label}).")
        seen_relationships.add(signature)
    return errors
