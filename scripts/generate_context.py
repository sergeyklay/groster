#!/usr/bin/env python3
"""
Script to generate a context file for LLM.

This script generates a context file for LLM that includes:
- A tree representation of all project files (respecting .gitignore)
- The contents of all project files (with configurable exclusions)

The context file is used to provide a comprehensive overview of the project to the LLM.

Usage:

python scripts/generate_context.py
"""

import argparse
import os
import pathlib
import subprocess

import chardet

ADDITIONAL_EXCLUDE_DIRS = [
    "__pycache__",
    ".cursor",
    ".devcontainer",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vscode",
    "build",
    "cache",
    "coverage",
    "data",
    "dist",
    "fixtures",
    "node_modules",
]

ADDITIONAL_EXCLUDE_FILES = [
    ".coderabbit.yaml",
    ".pre-commit-config.yaml",
    ".python-version",
    "CODEOWNERS",
    "context.md",
    "defaults.mk",
    "Makefile",
    "pse.code-workspace",
]

ADDITIONAL_EXCLUDE_EXTENSIONS = [
    ".csv",
    ".json",
    ".lock",
    ".pyc",
]

# Maximum file size to read (1MB)
MAX_FILE_SIZE_BYTES = 1024 * 1024

# Maximum content to show for truncated files (100KB)
TRUNCATE_SIZE_BYTES = 100 * 1024


def is_excluded(
    path: str,
    exclude_dirs: list[str],
    exclude_files: list[str],
    exclude_extensions: list[str],
) -> bool:
    """
    Check if a file or directory should be excluded based on exclusion lists.

    Args:
        path: Path to check
        exclude_dirs: List of directory names to exclude
        exclude_files: List of filenames to exclude
        exclude_extensions: List of file extensions to exclude

    Returns:
        bool: True if the path should be excluded, False otherwise
    """
    path_obj = pathlib.Path(path)

    for parent in path_obj.parents:
        if parent.name in exclude_dirs:
            return True

    if path_obj.name in exclude_files:
        return True

    if path_obj.suffix in exclude_extensions:
        return True

    return False


def is_ignored_by_git(path: str, repo_root: str) -> bool:
    """
    Check if a file is ignored by git.

    Args:
        path: Path to check
        repo_root: Root of the git repository

    Returns:
        bool: True if the file is ignored by git, False otherwise
    """
    rel_path = os.path.relpath(path, repo_root)
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", rel_path],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        # If there's any error running git, assume not ignored
        return False


def list_all_files(
    root_dir: str,
    exclude_dirs: list[str],
    exclude_files: list[str],
    exclude_extensions: list[str],
) -> list[str]:
    """
    Recursively list all files in a directory, respecting exclusions.

    Args:
        root_dir: Root directory to start listing from
        exclude_dirs: List of directory names to exclude
        exclude_files: List of filenames to exclude
        exclude_extensions: List of file extensions to exclude

    Returns:
        List[str]: List of file paths
    """
    all_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for filename in filenames:
            full_path = os.path.join(dirpath, filename)

            if is_excluded(full_path, exclude_dirs, exclude_files, exclude_extensions):
                continue

            if is_ignored_by_git(full_path, root_dir):
                continue

            all_files.append(full_path)

    return sorted(all_files)


def generate_tree(root_dir: str) -> str:
    """
    Generate a tree representation of files using the tree command-line utility.

    Args:
        root_dir: Root directory

    Returns:
        str: Tree representation
    """
    exclude_pattern = "|".join(ADDITIONAL_EXCLUDE_DIRS)
    always_exclude = "|".join([".DS_Store"])

    try:
        result = subprocess.run(
            ["tree", "-a", "-I", exclude_pattern + "|" + always_exclude],
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        tree_output = result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error generating tree: {e}\n{e.stderr}"
    except FileNotFoundError:
        return (
            "Error: 'tree' command not found. "
            "Please install it using your package manager."
        )

    return f"## Project Tree\n\n```\n{tree_output}\n```\n"


def _decode_file_content(raw_content: bytes, file_path: str) -> tuple[str, bool]:
    """
    Decode file content from bytes, handling different encodings and binary files.

    Args:
        raw_content: Raw file content as bytes
        file_path: Path to the file (for context in error messages)

    Returns:
        tuple: (decoded_content, is_binary) where is_binary indicates if file is binary
    """
    if not raw_content:
        return "", False

    if b"\x00" in raw_content:
        return "", True

    encoding = "utf-8"

    detected = chardet.detect(raw_content)
    if detected:
        encoding = detected.get("encoding")
        if (
            encoding
            and encoding.lower() in ["windows-1254", "iso-8859-1"]
            and detected.get("confidence", 0) < 0.7
        ):
            encoding = "utf-8"

    encodings_to_try = [encoding, "utf-8", "latin-1", "cp1252", "iso-8859-1"]

    for enc in encodings_to_try:
        try:
            decoded_content = raw_content.decode(enc, errors="replace")
            replacement_ratio = (
                decoded_content.count("\ufffd") / len(decoded_content)
                if decoded_content
                else 0
            )
            if replacement_ratio < 0.1:
                return decoded_content, False
        except (UnicodeDecodeError, LookupError):
            continue

    return "", True


def generate_file_contents(
    files: list[str],
    root_dir: str,
    content_exclude_dirs: list[str],
) -> str:
    """
    Generate markdown with file contents.

    Args:
        files: List of file paths
        root_dir: Root directory
        content_exclude_dirs: List of directories to exclude from content inclusion

    Returns:
        str: Markdown representation of file contents
    """

    content_lines = ["## File Contents"]

    for file_path in files:
        # Skip files in content exclude directories
        if any(excl_dir in file_path for excl_dir in content_exclude_dirs):
            continue

        rel_path = os.path.relpath(file_path, root_dir)

        try:
            # Check file size before reading
            file_size = os.path.getsize(file_path)

            if file_size > MAX_FILE_SIZE_BYTES:
                content_lines.append(f"\n### {rel_path}\n")
                content_lines.append(
                    f"*File too large ({file_size:,} bytes), skipped*\n"
                )
                continue

            # Read file content in binary mode to handle encoding issues
            with open(file_path, "rb") as f:
                if file_size > TRUNCATE_SIZE_BYTES:
                    # Read only first part of large files
                    raw_content = f.read(TRUNCATE_SIZE_BYTES)
                    truncated = True
                else:
                    raw_content = f.read()
                    truncated = False

            file_content, is_binary = _decode_file_content(raw_content, file_path)

            content_lines.append(f"\n### {rel_path}\n")
            if is_binary:
                content_lines.append("*Binary file, content not displayed*\n")
            elif file_content:
                content_lines.append(f"```{get_language_from_extension(file_path)}")
                content_lines.append(file_content)
                if truncated:
                    content_lines.append(
                        f"\n... (truncated at {TRUNCATE_SIZE_BYTES:,} bytes)"
                    )
                content_lines.append("```")
            else:
                content_lines.append("This file is empty.\n")
        except Exception as e:
            content_lines.append(f"\n### {rel_path}\n")
            content_lines.append(f"*Error reading file: {str(e)}*\n")

    return "\n".join(content_lines)


def get_language_from_extension(file_path: str) -> str:
    """
    Get the language identifier for code blocks based on file extension.

    Args:
        file_path: Path to the file

    Returns:
        str: Language identifier for markdown code blocks
    """
    ext = os.path.splitext(file_path)[1].lower()

    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".md": "markdown",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".sh": "bash",
        ".txt": "",
    }

    return language_map.get(ext, "")


def main():
    """Main function to parse arguments and execute document generation."""
    parser = argparse.ArgumentParser(
        description="Generate project documentation with file tree and contents"
    )
    parser.add_argument(
        "--output", default="docs/context.md", help="Output markdown file path"
    )
    parser.add_argument("--root", default=".", help="Root directory of the project")
    parser.add_argument(
        "--content-exclude",
        default="fixtures",
        help="Comma-separated list of directories to exclude from content",
    )
    parser.add_argument(
        "--default-content-exclude",
        default=".venv,.git,tests,fixtures,scripts",
        help="Default directories to exclude from content",
    )
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)
    output_file = os.path.abspath(args.output)

    content_exclude_dirs = {
        d.strip() for d in args.content_exclude.split(",") if d.strip()
    }
    default_excludes = {
        d.strip() for d in args.default_content_exclude.split(",") if d.strip()
    }
    content_exclude_dirs.update(default_excludes)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    all_files = list_all_files(
        root_dir,
        ADDITIONAL_EXCLUDE_DIRS,
        ADDITIONAL_EXCLUDE_FILES,
        ADDITIONAL_EXCLUDE_EXTENSIONS,
    )

    tree_content = generate_tree(root_dir)

    file_contents = generate_file_contents(
        all_files, root_dir, list(content_exclude_dirs)
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Project Structure\n\n")
        f.write(tree_content)
        f.write("\n")
        f.write(file_contents)

    print(f"Project documentation generated at {output_file}")


if __name__ == "__main__":
    main()
