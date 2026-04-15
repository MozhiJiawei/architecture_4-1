from __future__ import annotations

from copy import deepcopy
from typing import Any


STYLE_PROFILES: dict[str, dict[str, Any]] = {
    "ref-default": {
        "background": "#ffffff",
        "defaults": {
            "group": {
                "fillColor": "#f8f9fa",
                "strokeColor": "#6c757d",
                "fontColor": "#111827",
            },
            "node": {
                "fillColor": "#ffffff",
                "strokeColor": "#1f2937",
                "fontColor": "#111827",
            },
            "edge": {
                "strokeColor": "#374151",
                "fontColor": "#374151",
            },
        },
        "roles": {
            "neutral": {
                "fillColor": "#f8f9fa",
                "strokeColor": "#6c757d",
                "fontColor": "#111827",
            },
            "blue": {
                "fillColor": "#dae8fc",
                "strokeColor": "#6c8ebf",
                "fontColor": "#1f2937",
            },
            "green": {
                "fillColor": "#d5e8d4",
                "strokeColor": "#82b366",
                "fontColor": "#1f2937",
            },
            "yellow": {
                "fillColor": "#fff2cc",
                "strokeColor": "#d6b656",
                "fontColor": "#1f2937",
            },
            "purple": {
                "fillColor": "#e1d5e7",
                "strokeColor": "#9673a6",
                "fontColor": "#1f2937",
            },
            "entry-surface": {
                "fillColor": "#dae8fc",
                "strokeColor": "#6c8ebf",
                "fontColor": "#1f2937",
            },
            "agent-core": {
                "fillColor": "#e1d5e7",
                "strokeColor": "#9673a6",
                "fontColor": "#1f2937",
            },
            "capability-runtime": {
                "fillColor": "#d5e8d4",
                "strokeColor": "#82b366",
                "fontColor": "#1f2937",
            },
            "external-system": {
                "fillColor": "#fff2cc",
                "strokeColor": "#d6b656",
                "fontColor": "#1f2937",
            },
            "state-subsystem": {
                "fillColor": "#d5e8d4",
                "strokeColor": "#82b366",
                "fontColor": "#1f2937",
            },
            "automation-subsystem": {
                "fillColor": "#d5e8d4",
                "strokeColor": "#82b366",
                "fontColor": "#1f2937",
            },
            "integration-surface": {
                "fillColor": "#dae8fc",
                "strokeColor": "#6c8ebf",
                "fontColor": "#1f2937",
            },
            "runtime-service": {
                "fillColor": "#e1d5e7",
                "strokeColor": "#9673a6",
                "fontColor": "#1f2937",
            },
            "capability-subsystem": {
                "fillColor": "#d5e8d4",
                "strokeColor": "#82b366",
                "fontColor": "#1f2937",
            },
        },
    }
}


STYLE_KEYS = ("fillColor", "strokeColor", "fontColor")


def merge_style(*styles: dict[str, Any] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for style in styles:
        if not isinstance(style, dict):
            continue
        for key in STYLE_KEYS:
            value = style.get(key)
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()
    return merged


def resolve_style_profile(view_model: dict[str, Any]) -> dict[str, Any]:
    profile_name = str(view_model.get("style_profile") or "ref-default").strip() or "ref-default"
    profile = deepcopy(STYLE_PROFILES.get(profile_name, STYLE_PROFILES["ref-default"]))
    overrides = view_model.get("palette_overrides")
    if isinstance(overrides, dict):
        defaults = overrides.get("defaults")
        if isinstance(defaults, dict):
            for section in ("group", "node", "edge"):
                if isinstance(defaults.get(section), dict):
                    profile["defaults"][section] = merge_style(profile["defaults"].get(section), defaults[section])
        roles = overrides.get("roles")
        if isinstance(roles, dict):
            for role_name, role_style in roles.items():
                if isinstance(role_name, str) and isinstance(role_style, dict):
                    profile["roles"][role_name] = merge_style(profile["roles"].get(role_name), role_style)
    return profile


def role_style(profile: dict[str, Any], role_name: str | None) -> dict[str, str]:
    if not role_name:
        return {}
    roles = profile.get("roles")
    if not isinstance(roles, dict):
        return {}
    role = roles.get(role_name)
    return merge_style(role if isinstance(role, dict) else None)


def effective_subject_style(
    profile: dict[str, Any],
    subject_type: str,
    subject: dict[str, Any] | None,
) -> dict[str, str]:
    defaults = profile.get("defaults")
    base = {}
    if isinstance(defaults, dict):
        section = defaults.get(subject_type)
        if isinstance(section, dict):
            base = merge_style(section)

    if not isinstance(subject, dict):
        return base

    explicit_role = subject.get("color_role")
    resolved_role = str(explicit_role).strip() if isinstance(explicit_role, str) and explicit_role.strip() else None
    explicit_style = subject.get("style")
    return merge_style(base, role_style(profile, resolved_role), explicit_style if isinstance(explicit_style, dict) else None)
