from __future__ import annotations

from typing import Any

from .catalog import CATALOG_ALLOWED_COLUMNS
from .render import normalized_element_type


def validate_use_case_view(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(model.get("view") or "").strip().lower() != "use-case":
        errors.append("Use-case validator only accepts view='use-case'.")

    elements = [item for item in (model.get("elements") or []) if isinstance(item, dict)]
    if not elements:
        errors.append("Use-case view must include at least one element.")

    element_ids = {str(element.get("id") or "") for element in elements if str(element.get("id") or "")}
    if len(element_ids) != len([element for element in elements if str(element.get("id") or "")]):
        errors.append("Use-case view contains duplicate element ids.")
    boundary_ids = {
        str(element.get("id") or "")
        for element in elements
        if normalized_element_type(element.get("type")) == "system_boundary"
    }
    system_boundary = model.get("system_boundary")
    if isinstance(system_boundary, dict) and str(system_boundary.get("id") or ""):
        boundary_ids.add(str(system_boundary.get("id") or ""))
    group_ids = {
        str(group.get("id") or "")
        for group in (model.get("groups") or [])
        if isinstance(group, dict) and str(group.get("id") or "")
    }

    for element in elements:
        element_id = str(element.get("id") or "")
        if not element_id:
            errors.append("Use-case element is missing id.")
        group_id = str(element.get("group") or "")
        if group_id and group_ids and group_id not in group_ids:
            errors.append(f"Use-case element {element_id} references unknown group {group_id}.")
        boundary_id = str(element.get("boundary") or "")
        if boundary_id and boundary_ids and boundary_id not in boundary_ids:
            errors.append(f"Use-case element {element_id} references unknown boundary {boundary_id}.")

    for relationship in list(model.get("relationships") or []) + list(model.get("associations") or []):
        if not isinstance(relationship, dict):
            continue
        relationship_id = str(relationship.get("id") or "")
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if source not in element_ids:
            errors.append(f"Use-case relationship {relationship_id} references unknown source {source}.")
        if target not in element_ids:
            errors.append(f"Use-case relationship {relationship_id} references unknown target {target}.")
    return errors


def validate_use_case_catalog(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(model.get("view") or "").strip().lower() != "use-case-catalog":
        errors.append("Use-case catalog validator only accepts view='use-case-catalog'.")

    columns = model.get("catalog_columns")
    if columns is not None and columns != CATALOG_ALLOWED_COLUMNS:
        errors.append("use-case-catalog.catalog_columns must be exactly: 编号, 用例, 主参与者, 入口面, 优先级, 说明.")

    actors = [item for item in (model.get("actors") or []) if isinstance(item, dict)]
    use_cases = [item for item in (model.get("use_cases") or []) if isinstance(item, dict)]
    if not use_cases:
        errors.append("Use-case catalog view requires a non-empty top-level use_cases array.")

    actor_ids = {str(actor.get("id") or "") for actor in actors if str(actor.get("id") or "")}
    use_case_ids: set[str] = set()
    codes: set[str] = set()
    for use_case in use_cases:
        use_case_id = str(use_case.get("id") or "")
        code = str(use_case.get("code") or "")
        if not use_case_id:
            errors.append("Use-case catalog row is missing id.")
        if use_case_id in use_case_ids:
            errors.append(f"Duplicate use-case catalog id {use_case_id}.")
        use_case_ids.add(use_case_id)
        if code:
            if code in codes:
                errors.append(f"Duplicate use-case catalog code {code}.")
            codes.add(code)
        primary_actor = str(use_case.get("primary_actor") or "")
        if primary_actor and actor_ids and primary_actor not in actor_ids:
            errors.append(f"Use-case catalog row {use_case_id} references unknown actor {primary_actor}.")
        entry_surfaces = use_case.get("entry_surfaces")
        if entry_surfaces is not None and not isinstance(entry_surfaces, list):
            errors.append(f"Use-case catalog row {use_case_id} entry_surfaces must be a list.")
    return errors
