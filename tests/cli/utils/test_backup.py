# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pathlib
from unittest.mock import patch

import click
import pytest

from agent_starter_pack.cli.utils.backup import create_project_backup


@pytest.fixture()
def project_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a sample project directory for testing."""
    project = tmp_path / "my-project"
    project.mkdir()
    (project / "main.py").write_text("print('hello')")
    (project / "README.md").write_text("# My Project")
    sub = project / "app"
    sub.mkdir()
    (sub / "agent.py").write_text("root_agent = None")
    return project


class TestCreateProjectBackup:
    def test_success(self, project_dir: pathlib.Path, tmp_path: pathlib.Path) -> None:
        """Backup is created at the expected path and contains project files."""
        backup_base = tmp_path / "backups"
        with patch("agent_starter_pack.cli.utils.backup.BACKUP_BASE_DIR", backup_base):
            result = create_project_backup(project_dir, auto_approve=True)

        assert result is not None
        assert result.parent == backup_base
        assert result.name.startswith("my-project_")
        # Verify contents
        assert (result / "main.py").exists()
        assert (result / "README.md").exists()
        assert (result / "app" / "agent.py").exists()

    def test_excludes_standard_dirs(
        self, project_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        """Standard directories like .git, .venv, node_modules are excluded."""
        # Create dirs that should be excluded
        (project_dir / ".git").mkdir()
        (project_dir / ".git" / "HEAD").write_text("ref: refs/heads/main")
        (project_dir / ".venv").mkdir()
        (project_dir / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin")
        (project_dir / "node_modules").mkdir()
        (project_dir / "node_modules" / "pkg").write_text("{}")
        (project_dir / "__pycache__").mkdir()
        (project_dir / "__pycache__" / "mod.pyc").write_bytes(b"\x00")

        backup_base = tmp_path / "backups"
        with patch("agent_starter_pack.cli.utils.backup.BACKUP_BASE_DIR", backup_base):
            result = create_project_backup(project_dir, auto_approve=True)

        assert result is not None
        assert not (result / ".git").exists()
        assert not (result / ".venv").exists()
        assert not (result / "node_modules").exists()
        assert not (result / "__pycache__").exists()
        # But normal files should be there
        assert (result / "main.py").exists()

    def test_creates_parent_dirs(
        self, project_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        """BACKUP_BASE_DIR is auto-created if it doesn't exist."""
        backup_base = tmp_path / "deep" / "nested" / "backups"
        assert not backup_base.exists()

        with patch("agent_starter_pack.cli.utils.backup.BACKUP_BASE_DIR", backup_base):
            result = create_project_backup(project_dir, auto_approve=True)

        assert result is not None
        assert backup_base.exists()

    def test_failure_auto_approve_returns_none(
        self, project_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        """When backup fails with auto_approve=True, returns None silently."""
        backup_base = tmp_path / "backups"
        with (
            patch("agent_starter_pack.cli.utils.backup.BACKUP_BASE_DIR", backup_base),
            patch(
                "agent_starter_pack.cli.utils.backup.shutil.copytree",
                side_effect=OSError("disk full"),
            ),
        ):
            result = create_project_backup(project_dir, auto_approve=True)

        assert result is None

    def test_failure_user_cancels_raises_abort(
        self, project_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        """When backup fails and user says no, raises click.Abort."""
        backup_base = tmp_path / "backups"
        with (
            patch("agent_starter_pack.cli.utils.backup.BACKUP_BASE_DIR", backup_base),
            patch(
                "agent_starter_pack.cli.utils.backup.shutil.copytree",
                side_effect=OSError("disk full"),
            ),
            patch(
                "agent_starter_pack.cli.utils.backup.click.confirm",
                return_value=False,
            ),
            pytest.raises(click.Abort),
        ):
            create_project_backup(project_dir, auto_approve=False)

    def test_failure_user_continues_returns_none(
        self, project_dir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
        """When backup fails and user says yes, returns None."""
        backup_base = tmp_path / "backups"
        with (
            patch("agent_starter_pack.cli.utils.backup.BACKUP_BASE_DIR", backup_base),
            patch(
                "agent_starter_pack.cli.utils.backup.shutil.copytree",
                side_effect=OSError("disk full"),
            ),
            patch(
                "agent_starter_pack.cli.utils.backup.click.confirm",
                return_value=True,
            ),
        ):
            result = create_project_backup(project_dir, auto_approve=False)

        assert result is None
