#!/usr/bin/env python3
import argparse
import copy
import os
from pathlib import Path
from xml.sax.saxutils import escape

import yaml


def load_mapping(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("profile must be a YAML mapping: {}".format(path))
    return data


def deep_merge(base, overlay):
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_profile(path, overlay_path):
    profile = load_mapping(path)
    if overlay_path:
        profile = deep_merge(profile, load_mapping(overlay_path))
    return profile


def project_xml(project, default_revision):
    name = escape(str(project["name"]))
    path = escape(str(project["path"]))
    remote = escape(str(project.get("remote", "github")))
    revision = escape(str(project.get("revision", default_revision)))
    return '  <project name="{}" path="{}" remote="{}" revision="{}" />'.format(
        name,
        path,
        remote,
        revision,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profile-overlay")
    parser.add_argument("--android-root", required=True)
    args = parser.parse_args()

    overlay_path = (
        args.profile_overlay
        or os.environ.get("PROFILE_OVERLAY_PATH")
        or os.environ.get("PROFILE_OVERLAY")
    )
    profile = load_profile(args.profile, overlay_path)
    lineage = profile.get("lineage", {})
    projects = lineage.get("extra_projects", [])
    if not projects:
        return

    local_manifests = Path(args.android_root) / ".repo" / "local_manifests"
    local_manifests.mkdir(parents=True, exist_ok=True)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<manifest>"]
    for project in projects:
        lines.append(project_xml(project, lineage["branch"]))
    lines.append("</manifest>")
    (local_manifests / "rosie-local-ha.xml").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
