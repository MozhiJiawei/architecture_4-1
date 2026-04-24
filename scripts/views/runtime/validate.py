from __future__ import annotations

from typing import Any


def validate_runtime_view(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(model.get("view") or "").strip().lower() != "runtime":
        errors.append("Runtime validator only accepts view='runtime'.")

    elements = [item for item in (model.get("elements") or []) if isinstance(item, dict)]
    relationships = [item for item in (model.get("relationships") or []) if isinstance(item, dict)]
    primary_paths = [item for item in (model.get("primary_paths") or []) if isinstance(item, dict)]
    if not primary_paths:
        errors.append("Runtime view requires a non-empty primary_paths array.")

    element_ids = {str(element.get("id") or "") for element in elements if str(element.get("id") or "")}
    if len(element_ids) != len([element for element in elements if str(element.get("id") or "")]):
        errors.append("Runtime view contains duplicate element ids.")
    relationship_ids = {
        str(relationship.get("id") or "")
        for relationship in relationships
        if str(relationship.get("id") or "")
    }
    if len(relationship_ids) != len([relationship for relationship in relationships if str(relationship.get("id") or "")]):
        errors.append("Runtime view contains duplicate relationship ids.")
    for relationship in relationships:
        relationship_id = str(relationship.get("id") or "")
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if source not in element_ids:
            errors.append(f"Runtime relationship {relationship_id} references unknown source {source}.")
        if target not in element_ids:
            errors.append(f"Runtime relationship {relationship_id} references unknown target {target}.")

    for path in primary_paths:
        path_id = str(path.get("id") or "")
        step_ids = [str(item) for item in (path.get("main_step_ids") or []) if str(item)]
        branch_step_ids = [
            str(item)
            for branch in (path.get("branches") or [])
            if isinstance(branch, dict)
            for item in (branch.get("step_ids") or [])
            if str(item)
        ]
        if not step_ids and not branch_step_ids:
            errors.append(f"Runtime primary path {path_id} has no step ids.")
        for step_id in step_ids + branch_step_ids:
            if step_id not in relationship_ids:
                errors.append(f"Runtime primary path {path_id} references unknown relationship {step_id}.")
    return errors
