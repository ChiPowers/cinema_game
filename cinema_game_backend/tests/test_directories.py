"""Tests for directories module path resolution utilities."""

import os

from cinema_game_backend import directories


class TestDirectories:
    """Test path resolution functions."""

    def test_directories_exist(self):
        """Test that all directories returned by functions exist."""
        assert os.path.isdir(directories.base())
        assert os.path.isdir(directories.code())
        assert os.path.isdir(directories.tests())
        assert os.path.isdir(directories.secrets())

    def test_base_directory_contains_readme(self):
        """Test that base directory contains README.md."""
        assert os.path.exists(directories.base("README.md"))

    def test_code_directory_contains_init(self):
        """Test that code directory contains __init__.py."""
        assert os.path.exists(directories.code("__init__.py"))

    def test_tests_directory_contains_files(self):
        """Test that tests directory contains test files."""
        # At least one test file should exist
        test_files = [
            directories.tests("test_models.py"),
            directories.tests("test_routes.py"),
            directories.tests("test_config.py"),
        ]
        assert any(os.path.exists(f) for f in test_files), (
            f"No test files found in tests directory"
        )

    def test_secrets_directory_contains_env_example(self):
        """Test that secrets directory contains .env.example."""
        assert os.path.exists(directories.secrets(".env.example"))

    def test_qualifyname_without_filename(self):
        """Test qualifyname returns directory when no filename provided."""
        result = directories.qualifyname("/some/path")
        assert result == "/some/path"

    def test_qualifyname_with_filename(self):
        """Test qualifyname joins directory and filename."""
        result = directories.qualifyname("/some/path", "file.txt")
        assert result == os.path.join("/some/path", "file.txt")
