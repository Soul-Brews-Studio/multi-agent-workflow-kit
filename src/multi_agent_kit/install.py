from __future__ import annotations

from dataclasses import dataclass
import os
import re
import shutil
import stat
from importlib import resources as importlib_resources

try:  # Python 3.14 removed Traversable from importlib.abc
    from importlib.resources.abc import Traversable
except ImportError:  # Fallback for Python <3.9 where resources.abc is absent
    from importlib.abc import Traversable  # type: ignore[attr-defined]
from pathlib import Path
from typing import Iterator
from importlib.metadata import PackageNotFoundError, version as get_package_version

ASSET_PACKAGE = "multi_agent_kit"
ASSET_ROOT_NAME = "assets"
ITEM_MAP = (
    (".agents", ".agents"),    # Toolkit files go to .agents/
    ("agents", "agents"),      # Gitignore-only directory for worktrees
    (".claude", ".claude"),    # Claude commands and configuration
    (".codex", ".codex"),      # Codex CLI prompts and cache scaffolding
    ("MAW-AGENTS.md", "MAW-AGENTS.md"),  # Guide for human/AI collaborators
)

ENVRC_BEGIN_MARKER = "# === BEGIN Multi-Agent Workflow Kit ==="
ENVRC_END_MARKER = "# === END Multi-Agent Workflow Kit ==="


@dataclass(frozen=True)
class CopyPlan:
    source: Traversable
    destination: Path


class AssetInstaller:
    def __init__(
        self,
        target: Path,
        force: bool = False,
        create_agents_gitignore: bool = False,
    ) -> None:
        self.target = target
        self.force = force
        self.create_agents_gitignore = create_agents_gitignore
        self.package_version = self._detect_package_version()

    def ensure_assets(self) -> list[Path]:
        written: list[Path] = []
        for source_name, dest_name in ITEM_MAP:
            # Special handling for agents directory
            if source_name == "agents" and dest_name == "agents":
                # Create agents directory with minimal .gitignore
                destination = self.target / dest_name
                destination.mkdir(parents=True, exist_ok=True)
                gitignore = destination / ".gitignore"
                if self.create_agents_gitignore:
                    if not gitignore.exists() or self.force:
                        gitignore.write_text("# Ignore all agent worktrees\n*\n!.gitignore\n")
                        written.append(gitignore)
                elif gitignore.exists():
                    gitignore.unlink()
                continue

            source = self._asset_root().joinpath(source_name)
            destination = self.target / dest_name
            self._copy(source, destination, written)

        # Handle .envrc separately with smart merge
        self._ensure_envrc(written)
        self._ensure_root_gitignore(written)
        self._write_version_marker(written)
        return written

    def _asset_root(self) -> Traversable:
        return importlib_resources.files(ASSET_PACKAGE).joinpath(ASSET_ROOT_NAME)

    def _copy(self, source: Traversable, destination: Path, written: list[Path]) -> None:
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            # Handle directory with children
            try:
                for child in source.iterdir():
                    self._copy(child, destination / child.name, written)
            except (AttributeError, NotImplementedError):
                # Some Traversable implementations don't support iterdir on certain directories
                pass
            return

        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not self.force:
            return

        with importlib_resources.as_file(source) as src_path:
            shutil.copy2(src_path, destination)
            # Ensure .sh files are executable
            if destination.suffix == ".sh":
                current_mode = os.stat(destination).st_mode
                os.chmod(destination, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        written.append(destination)

    def _ensure_envrc(self, written: list[Path]) -> None:
        """Smart merge .envrc with existing content, using marked sections."""
        envrc_path = self.target / ".envrc"
        source = self._asset_root().joinpath(".envrc")

        # Read toolkit config
        with importlib_resources.as_file(source) as src_path:
            toolkit_config = src_path.read_text()

        # Wrap toolkit config in markers
        wrapped_config = f"{ENVRC_BEGIN_MARKER}\n{toolkit_config.rstrip()}\n{ENVRC_END_MARKER}\n"

        if not envrc_path.exists():
            # No existing .envrc, write wrapped config
            envrc_path.write_text(wrapped_config)
            written.append(envrc_path)
            return

        # Read existing .envrc
        existing_content = envrc_path.read_text()

        # Check if toolkit section already exists
        if ENVRC_BEGIN_MARKER in existing_content and ENVRC_END_MARKER in existing_content:
            if self.force:
                # Replace existing toolkit section
                import re
                pattern = rf"{re.escape(ENVRC_BEGIN_MARKER)}.*?{re.escape(ENVRC_END_MARKER)}\n?"
                new_content = re.sub(pattern, wrapped_config, existing_content, flags=re.DOTALL)
                envrc_path.write_text(new_content)
                written.append(envrc_path)
            # else: toolkit section exists, nothing to do
            return

        # Append toolkit config to existing .envrc
        if not existing_content.endswith("\n"):
            existing_content += "\n"

        merged_content = existing_content + "\n" + wrapped_config
        envrc_path.write_text(merged_content)
        written.append(envrc_path)

    def _ensure_root_gitignore(self, written: list[Path]) -> None:
        gitignore_path = self.target / ".gitignore"
        marker = "# Added by Multi-Agent Workflow Kit"
        ignore_lines = [
            "/.agents",
            "/agents",
            "/.envrc",
            "/MAW-*",
            ".claude/settings.local.json",
            ".claude/*",
            "!.claude/commands/",
            ".codex/*",
            "!.codex/prompts/",
            "!.codex/prompts/**",
        ]

        # Additional ignore patterns for toolkit-generated files
        toolkit_generated = [
            ".claude/commands/maw.*",
            ".claude/commands/maw-*",
            ".codex/prompts/maw*.md",
        ]
        ignore_lines.extend(toolkit_generated)

        try:
            existing = gitignore_path.read_text()
        except FileNotFoundError:
            content = marker + "\n" + "\n".join(ignore_lines) + "\n"
            gitignore_path.write_text(content)
            written.append(gitignore_path)
            return

        lines = [line.strip() for line in existing.splitlines()]

        append_lines = [entry for entry in ignore_lines if entry not in lines]

        if not append_lines:
            return

        append_text = ""
        if not existing.endswith("\n"):
            append_text += "\n"
        if marker not in existing:
            append_text += f"\n{marker}\n"
        append_text += "\n".join(append_lines) + "\n"

        gitignore_path.write_text(existing + append_text)
        written.append(gitignore_path)

    def _write_version_marker(self, written: list[Path]) -> None:
        if not self.package_version:
            return

        version_path = self.target / ".agents" / "VERSION"
        version_path.parent.mkdir(parents=True, exist_ok=True)

        if version_path.exists() and not self.force:
            return

        version_path.write_text(f"{self._format_display_version(self.package_version)}\n")
        written.append(version_path)

    @staticmethod
    def _detect_package_version() -> str | None:
        try:
            return get_package_version("multi-agent-kit")
        except PackageNotFoundError:
            return None

    @staticmethod
    def _format_display_version(raw: str) -> str:
        if not raw:
            return raw

        pattern = r"^(?P<base>\d+(?:\.\d+)*)(?:(?P<pre>a|b|rc)(?P<num>\d+))?$"
        match = re.match(pattern, raw)
        if not match:
            return raw

        base = match.group("base")
        pre = match.group("pre")
        if not pre:
            return raw

        num = match.group("num") or ""
        label_map = {"a": "alpha", "b": "beta", "rc": "rc"}
        label = label_map.get(pre, pre)

        suffix = f"-{label}"
        if num and num != "0":
            suffix += f".{num}"

        return base + suffix


def missing_assets(target: Path) -> Iterator[str]:
    for _, dest_name in ITEM_MAP:
        if not (target / dest_name).exists():
            yield dest_name
