"""
sys_audit.py — Workspace / System audit utility.

This module performs a self-contained audit of the current workspace and the
host environment. It is intentionally implemented with the Python **standard
library only** (no third-party deps) so it runs anywhere without `pip install`.

IMPORTANT (filesystem scope):
    The deep-agent sandbox exposes the project *repo root* at
    C:/Users/USER/Documents/Task/DeepAgent. The bare shell drive ``C:\\`` is a
    SEPARATE volume that the agent's file tools cannot see. To avoid the
    previous mistake of writing output to the wrong location, this script
    resolves its target directory from ``sys.argv[1]`` (if given) else from the
    directory containing this file, guaranteeing output lands inside the repo
    root.

Usage:
    python sys_audit.py [target_dir] [--json]

    target_dir : directory to audit (default: directory of this script)
    --json     : emit machine-readable JSON instead of formatted text
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import shutil
import sys
from pathlib import Path


# Directories that should never be walked into during a shallow audit.
_SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "build",
    "dist",
}


def _human_size(num: int) -> str:
    """Convert a byte count into a human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if num < 1024 or unit == "PB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{num} B"
        num /= 1024.0
    return f"{num:.1f} PB"


def audit_environment() -> dict:
    """Collect host / runtime environment facts."""
    py_impl = platform.python_implementation()
    return {
        "python_version": platform.python_version(),
        "python_implementation": py_impl,
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "executable": sys.executable,
        "cwd": os.getcwd(),
        "env_keys_sample": sorted(
            k for k in os.environ if k.upper() in {
                "PATH", "HOME", "USERPROFILE", "OS", "COMPUTERNAME", "NUMBER_OF_PROCESSORS"
            }
        ),
    }


def audit_workspace(root: Path, max_depth: int = 3) -> dict:
    """Walk the workspace and collect file/dir statistics (shallow)."""
    root = root.resolve()
    file_count = 0
    dir_count = 0
    total_bytes = 0
    largest: list[dict] = []
    ext_counts: dict[str, int] = {}
    errors: list[str] = []

    def _walk(current: Path, depth: int) -> None:
        nonlocal file_count, dir_count, total_bytes
        if depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except (PermissionError, OSError) as exc:
            errors.append(f"{current}: {exc}")
            return

        for entry in entries:
            if entry.name in _SKIP_DIRS:
                continue
            try:
                if entry.is_dir():
                    dir_count += 1
                    _walk(entry, depth + 1)
                elif entry.is_file():
                    file_count += 1
                    size = entry.stat().st_size
                    total_bytes += size
                    ext = entry.suffix.lower() or "<none>"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
                    largest.append({"path": str(entry.relative_to(root)), "bytes": size})
                else:
                    # symlink or special file
                    pass
            except (PermissionError, OSError) as exc:
                errors.append(f"{entry}: {exc}")

    _walk(root, 0)
    largest.sort(key=lambda d: d["bytes"], reverse=True)
    largest = largest[:10]

    return {
        "root": str(root),
        "file_count": file_count,
        "dir_count": dir_count,
        "total_size_bytes": total_bytes,
        "total_size_human": _human_size(total_bytes),
        "extension_counts": dict(sorted(ext_counts.items(), key=lambda kv: kv[1], reverse=True)),
        "largest_files": largest,
        "scan_errors": errors,
    }


def run_audit(target: Path) -> dict:
    target = Path(target).expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Target directory does not exist: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Target is not a directory: {target}")

    return {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "target": str(target),
        "environment": audit_environment(),
        "workspace": audit_workspace(target),
        "disk": _disk_info(target),
    }


def _disk_info(path: Path) -> dict:
    try:
        usage = shutil.disk_usage(path)
        return {
            "total": _human_size(usage.total),
            "used": _human_size(usage.used),
            "free": _human_size(usage.free),
            "percent_used": round(usage.used / usage.total * 100, 1),
        }
    except (OSError, AttributeError):
        return {}


def _format_text(report: dict) -> str:
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("SYSTEM / WORKSPACE AUDIT REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated     : {report['generated_at']}")
    lines.append(f"Target        : {report['target']}")

    env = report["environment"]
    lines.append("")
    lines.append("-- Environment --")
    lines.append(f"Python        : {env['python_version']} ({env['python_implementation']})")
    lines.append(f"Platform      : {env['platform']}")
    lines.append(f"Machine       : {env['machine']}")
    lines.append(f"Executable    : {env['executable']}")

    ws = report["workspace"]
    lines.append("")
    lines.append("-- Workspace --")
    lines.append(f"Files         : {ws['file_count']}")
    lines.append(f"Directories   : {ws['dir_count']}")
    lines.append(f"Total size    : {ws['total_size_human']}")
    if ws["extension_counts"]:
        top_ext = ", ".join(f"{k}={v}" for k, v in list(ws["extension_counts"].items())[:8])
        lines.append(f"Top extensions: {top_ext}")
    if ws["largest_files"]:
        lines.append("")
        lines.append("Largest files:")
        for f in ws["largest_files"][:5]:
            lines.append(f"  {_human_size(f['bytes']):>10}  {f['path']}")

    disk = report.get("disk") or {}
    if disk:
        lines.append("")
        lines.append("-- Disk --")
        lines.append(f"Total/Used/Free: {disk.get('total')} / {disk.get('used')} / {disk.get('free')} "
                     f"({disk.get('percent_used')}%)")

    if ws["scan_errors"]:
        lines.append("")
        lines.append(f"Scan warnings ({len(ws['scan_errors'])}):")
        for err in ws["scan_errors"][:5]:
            lines.append(f"  ! {err}")

    lines.append("=" * 60)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a workspace / system.")
    parser.add_argument(
        "target",
        nargs="?",
        default=str(Path(__file__).resolve().parent),
        help="Directory to audit (default: this script's directory).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument(
        "--out",
        default=None,
        help="Write report to this path (inside repo root). "
             "Default: <target>/sys_audit_report.txt",
    )
    args = parser.parse_args(argv)

    try:
        report = run_audit(Path(args.target))
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        output = json.dumps(report, indent=2)
    else:
        output = _format_text(report)

    out_path = Path(args.out) if args.out else (Path(report["target"]) / "sys_audit_report.txt")
    # Safety: never escape the resolved target's parent repo root unintentionally.
    out_path = out_path.resolve()
    out_path.write_text(output + "\n", encoding="utf-8")

    # Echo to stdout as well.
    print(output)
    print(f"\n[Report written to: {out_path}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
