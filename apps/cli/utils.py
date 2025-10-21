from pathlib import Path


def data_path(base_dir: Path, *args: str) -> Path:
    """Construct a data file path from the given path components.

    Args:
        base_dir: Base directory to construct the path from.
        *args: Path components to join with hyphens (e.g., "guild", "members").
            At least one component is required.

    Returns:
        Path object pointing to DATA_PATH/component1-component2-....csv.

    Raises:
        ValueError: If no path components are provided.

    Example:
        >>> data_path(Path("data"), "guild", "roster")
        Path("/data/guild-roster.csv")
    """
    if not args:
        raise ValueError("At least one path component is required")

    local_path = "-".join(args).lstrip("/")
    return base_dir / f"{local_path}.csv"
