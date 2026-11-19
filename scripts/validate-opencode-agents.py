#!/usr/bin/env python3
"""Lightweight consistency checks for the repo-scoped OpenCode integration."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"{path.relative_to(ROOT)} has no YAML frontmatter")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        fail(f"{path.relative_to(ROOT)} has unterminated YAML frontmatter")
    return parts[0][4:]


def check_agent(filename: str, expected_mode: str, expected_model: str) -> str:
    path = ROOT / ".opencode" / "agents" / filename
    metadata = frontmatter(path)
    for key, expected in (
        ("mode", expected_mode),
        ("model", expected_model),
    ):
        if not re.search(rf"(?m)^{key}:\s*['\"]?{re.escape(expected)}['\"]?\s*$", metadata):
            fail(f"{path.relative_to(ROOT)} must set {key}: {expected}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
    if config.get("$schema") != "https://opencode.ai/config.json":
        fail("opencode.json must declare the OpenCode schema")
    if config.get("experimental", {}).get("subagent_depth") != 2:
        fail("OpenCode subagent_depth must be 2 for strategist -> collector nesting")

    strategist = check_agent(
        "continuous-delivery-strategist.md", "all", "github-copilot/gpt-6.1-terra"
    )
    collector = check_agent(
        "cd-evidence-collector.md", "subagent", "github-copilot/gpt-6-luna"
    )
    if not re.search(
        r"(?ms)^permission:\s*\n\s+task:\s*\n\s+['\"]?\*['\"]?:\s*deny\s*\n\s+cd-evidence-collector:\s*allow",
        frontmatter(ROOT / ".opencode" / "agents" / "continuous-delivery-strategist.md"),
    ):
        fail("strategist must explicitly allow the cd-evidence-collector subagent")
    strategist_metadata = frontmatter(
        ROOT / ".opencode" / "agents" / "continuous-delivery-strategist.md"
    )
    for denied_tool in ("bash", "glob", "grep", "webfetch", "skill"):
        if not re.search(rf"(?m)^\s+{denied_tool}:\s*deny\s*$", strategist_metadata):
            fail(f"strategist must not use {denied_tool} to collect evidence itself")
    if not re.search(r"(?ms)^permission:\s*.*?^\s+cd-discovery/summary\.md:\s*allow\s*$", strategist_metadata):
        fail("strategist must be allowed to write the summary report")
    if not re.search(r"(?m)^\s+cd-discovery/findings\.md:\s*allow\s*$", strategist_metadata):
        fail("strategist must be allowed to write the findings report")
    if "Do not scan source files" not in strategist:
        fail("strategist must preserve collector-only source-collection ownership")
    if "Do not broaden scope" not in collector or "Never modify source files" not in collector:
        fail("collector must retain bounded scope and read-only source constraints")
    collector_metadata = frontmatter(
        ROOT / ".opencode" / "agents" / "cd-evidence-collector.md"
    )
    if not re.search(
        r"(?ms)^permission:\s*\n\s+edit:\s*\n\s+['\"]?\*['\"]?:\s*deny\s*\n\s+cd-discovery/evidence\.md:\s*allow",
        collector_metadata,
    ):
        fail("collector must be limited to writing the canonical evidence file")
    for denied_tool in ("webfetch", "skill"):
        if not re.search(rf"(?m)^\s+{denied_tool}:\s*deny\s*$", collector_metadata):
            fail(f"collector must not use {denied_tool} outside the supplied collection protocol")

    print("OpenCode agent definitions and nested delegation config are consistent.")


if __name__ == "__main__":
    main()
