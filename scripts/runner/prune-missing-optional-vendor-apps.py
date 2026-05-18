#!/usr/bin/env python3
"""Prune generated vendor app modules for optional APK blobs that are absent."""

import argparse
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple


def optional_apk_modules(proprietary_files: Path, vendor_root: Path) -> List[str]:
    modules = []  # type: List[str]
    for raw_line in proprietary_files.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("-"):
            continue

        entry = line[1:].split(";", 1)[0].split("|", 1)[0]
        if ":" in entry:
            _, entry = entry.split(":", 1)
        if not entry.endswith(".apk"):
            continue

        blob_path = vendor_root / "proprietary" / entry
        if not blob_path.exists():
            modules.append(Path(entry).stem)
    return modules


def prune_android_mk(path: Path, missing_modules: Set[str]) -> bool:
    lines = path.read_text().splitlines(keepends=True)
    output = []  # type: List[str]
    changed = False
    index = 0

    while index < len(lines):
        if lines[index].strip() != "include $(CLEAR_VARS)":
            output.append(lines[index])
            index += 1
            continue

        start = index
        end = index
        module = None
        while end < len(lines):
            match = re.match(r"\s*LOCAL_MODULE\s*:=\s*(\S+)\s*$", lines[end])
            if match:
                module = match.group(1)
            if lines[end].strip() == "include $(BUILD_PREBUILT)":
                end += 1
                break
            end += 1

        block = lines[start:end]
        if module in missing_modules:
            changed = True
            while end < len(lines) and lines[end].strip() == "":
                end += 1
            index = end
            continue

        output.extend(block)
        index = end

    if changed:
        path.write_text("".join(output))
    return changed


def parse_package_block(lines: List[str], start: int) -> Tuple[List[str], int]:
    block = [lines[start]]
    index = start + 1
    while block[-1].rstrip().endswith("\\") and index < len(lines):
        block.append(lines[index])
        index += 1
    return block, index


def package_line_module(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    return stripped.rstrip("\\").strip() or None


def rewrite_package_block(block: List[str], missing_modules: Set[str]) -> Tuple[List[str], bool]:
    if not any(module in "".join(block) for module in missing_modules):
        return block, False

    header = block[0].split("\\", 1)[0].rstrip()
    modules = []  # type: List[str]
    for line in block[1:]:
        module = package_line_module(line)
        if module and module not in missing_modules:
            modules.append(module)
    if not modules:
        return [], True

    rewritten = [f"{header} \\\n"]
    for index, module in enumerate(modules):
        suffix = " \\\n" if index < len(modules) - 1 else "\n"
        rewritten.append(f"    {module}{suffix}")
    return rewritten, True


def prune_product_packages(path: Path, missing_modules: Set[str]) -> bool:
    lines = path.read_text().splitlines(keepends=True)
    output = []  # type: List[str]
    changed = False
    index = 0

    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("PRODUCT_PACKAGES") and "+=" in line:
            block, index = parse_package_block(lines, index)
            rewritten, block_changed = rewrite_package_block(block, missing_modules)
            output.extend(rewritten)
            changed = changed or block_changed
            continue

        output.append(line)
        index += 1

    if changed:
        path.write_text("".join(output))
    return changed


def copy_file_entry(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    return stripped.rstrip("\\").strip() or None


def copy_file_source(entry: str) -> Optional[str]:
    if ":" not in entry:
        return None
    source, _ = entry.split(":", 1)
    return source


def rewrite_copy_block(
    block: List[str],
    android_root: Path,
    missing_sources: List[str],
) -> Tuple[List[str], bool]:
    if not any("vendor/nvidia/shieldtablet/proprietary/" in line for line in block):
        return block, False

    header = block[0].split("\\", 1)[0].rstrip()
    entries = []  # type: List[str]
    changed = False

    for line in block[1:]:
        entry = copy_file_entry(line)
        if not entry:
            continue

        source = copy_file_source(entry)
        if (
            source
            and source.startswith("vendor/nvidia/shieldtablet/proprietary/")
            and not (android_root / source).exists()
        ):
            missing_sources.append(source)
            changed = True
            continue
        entries.append(entry)

    if not changed:
        return block, False
    if not entries:
        return [], True

    rewritten = [f"{header} \\\n"]
    for index, entry in enumerate(entries):
        suffix = " \\\n" if index < len(entries) - 1 else "\n"
        rewritten.append(f"    {entry}{suffix}")
    return rewritten, True


def prune_missing_product_copy_files(path: Path, android_root: Path) -> List[str]:
    lines = path.read_text().splitlines(keepends=True)
    output = []  # type: List[str]
    missing_sources = []  # type: List[str]
    changed = False
    index = 0

    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("PRODUCT_COPY_FILES") and "+=" in line:
            block, index = parse_package_block(lines, index)
            rewritten, block_changed = rewrite_copy_block(block, android_root, missing_sources)
            output.extend(rewritten)
            changed = changed or block_changed
            continue

        output.append(line)
        index += 1

    if changed:
        path.write_text("".join(output))
    return sorted(missing_sources)


def prune_missing_optional_vendor_apps(
    android_root: Path,
    device_path: str = "device/nvidia/shieldtablet",
    vendor_path: str = "vendor/nvidia/shieldtablet",
) -> Tuple[List[str], List[str]]:
    device_root = android_root / device_path
    vendor_root = android_root / vendor_path
    missing_modules = set(optional_apk_modules(device_root / "proprietary-files.txt", vendor_root))
    if missing_modules:
        prune_android_mk(vendor_root / "Android.mk", missing_modules)
        prune_product_packages(vendor_root / "shieldtablet-vendor.mk", missing_modules)
    missing_sources = prune_missing_product_copy_files(vendor_root / "shieldtablet-vendor.mk", android_root)
    return sorted(missing_modules), missing_sources


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--android-root", required=True, type=Path)
    parser.add_argument("--device-path", default="device/nvidia/shieldtablet")
    parser.add_argument("--vendor-path", default="vendor/nvidia/shieldtablet")
    args = parser.parse_args()

    pruned_modules, pruned_sources = prune_missing_optional_vendor_apps(
        args.android_root,
        args.device_path,
        args.vendor_path,
    )
    if pruned_modules:
        print("Pruned missing optional vendor APK modules: " + ", ".join(pruned_modules))
    else:
        print("No missing optional vendor APK modules detected.")

    if pruned_sources:
        print("Pruned missing vendor copy-file sources:")
        for source in pruned_sources:
            print(f"  - {source}")
    else:
        print("No missing vendor copy-file sources detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
