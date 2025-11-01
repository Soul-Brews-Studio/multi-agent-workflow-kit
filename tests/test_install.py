from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

from multi_agent_kit.install import AssetInstaller, missing_assets


def test_traversable_import_backward_compatibility(monkeypatch: pytest.MonkeyPatch) -> None:
    import multi_agent_kit.install as install
    import importlib.resources.abc as resources_abc

    # Default import should come from importlib.resources.abc on modern Python.
    assert install.Traversable is resources_abc.Traversable

    if sys.version_info >= (3, 14):
        return

    flag: dict[str, bool] = {}

    class StubModule(types.ModuleType):
        def __getattr__(self, name: str):  # type: ignore[override]
            flag["raised"] = True
            raise ImportError("Simulated missing attribute")

    with monkeypatch.context() as mp:
        mp.delitem(sys.modules, "multi_agent_kit.install", raising=False)
        mp.setitem(sys.modules, "importlib.resources.abc", StubModule("importlib.resources.abc"))
        fallback_module = importlib.import_module("multi_agent_kit.install")
        assert fallback_module.Traversable is importlib.import_module("importlib.abc").Traversable

    assert flag.get("raised") is True

    reloaded = importlib.reload(importlib.import_module("multi_agent_kit.install"))
    assert reloaded.Traversable is resources_abc.Traversable
    globals()["AssetInstaller"] = reloaded.AssetInstaller
    globals()["missing_assets"] = reloaded.missing_assets


def test_installer_creates_assets(tmp_path: Path) -> None:
    installer = AssetInstaller(tmp_path)
    assert list(missing_assets(tmp_path)) == [
        ".agents",
        "agents",
        ".claude",
        ".codex",
        "MAW-AGENTS.md",
    ]

    written = installer.ensure_assets()
    assert (tmp_path / ".agents").is_dir()
    assert (tmp_path / "agents").is_dir()
    assert not (tmp_path / "agents" / ".gitignore").exists()
    assert (tmp_path / ".claude").is_dir()
    assert (tmp_path / ".codex").is_dir()
    assert (tmp_path / "MAW-AGENTS.md").is_file()
    assert written  # some files were copied

    # second run without force should not rewrite files
    written_again = installer.ensure_assets()
    assert written_again == []
    assert list(missing_assets(tmp_path)) == []


def test_force_overwrites(tmp_path: Path) -> None:
    installer = AssetInstaller(tmp_path)
    installer.ensure_assets()

    target_doc = tmp_path / "MAW-AGENTS.md"
    target_doc.write_text("user modified")

    force_installer = AssetInstaller(tmp_path, force=True)
    written = force_installer.ensure_assets()
    assert target_doc.read_text() != "user modified"
    assert target_doc.is_file()
    assert target_doc in written
    assert written  # at least one file rewritten

    # ensure missing_assets still empty
    assert list(missing_assets(tmp_path)) == []


def test_agents_gitignore_opt_in(tmp_path: Path) -> None:
    create_installer = AssetInstaller(tmp_path, create_agents_gitignore=True)
    create_installer.ensure_assets()
    gitignore_path = tmp_path / "agents" / ".gitignore"
    assert gitignore_path.is_file()

    # Running again without the option should remove the file (for backwards compatibility)
    default_installer = AssetInstaller(tmp_path)
    default_installer.ensure_assets()
    assert not gitignore_path.exists()
