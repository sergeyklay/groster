"""Diff two alt-detection CSV snapshots and classify every changed assignment.

Compares an old alts CSV against a new one, cross-references the current
achievements CSV to classify each change as hidden-profile, standalone-left,
main-left-guild, member-left-guild, main-selection-change, group-absorbed,
or unknown, then prints a categorised report.

Usage:
    python scripts/diff_alts.py \
        --old data_v0.4.0/eu-terokkar-darq-side-of-the-moon-alts.csv \
        --new data/eu-terokkar-darq-side-of-the-moon-alts.csv \
        --achievements data/eu-terokkar-darq-side-of-the-moon-achievements.csv

Both alts CSVs must be from the same guild slug.

Exit codes:
    0 — no unknown changes (PASS)
    1 — one or more unknown changes (FAIL — potential regression)
    2 — bad arguments or unreadable/malformed input files
"""

import argparse
import csv
import os
import sys

CATEGORY_ORDER: list[str] = [
    "hidden-profile",
    "standalone-left",
    "main-left-guild",
    "member-left-guild",
    "main-selection-change",
    "group-absorbed",
    "unknown",
]


# ---------------------------------------------------------------------------
# Phase 2: Data loaders
# ---------------------------------------------------------------------------


def load_alts(path: str) -> dict[str, str]:
    """Read an alts CSV and return {character_name: main_name}.

    Args:
        path: Filesystem path to the alts CSV file.

    Returns:
        Mapping of every character name to their designated main name.
        Standalone mains map to themselves (name == main).
    """
    required = {"id", "name", "alt", "main"}
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = required - fieldnames
        if missing:
            print(
                f"Error: {path} is missing columns: {sorted(missing)}",
                file=sys.stderr,
            )
            sys.exit(2)
        return {row["name"]: row["main"] for row in reader}


def load_achievements(path: str) -> dict[str, tuple[int, int]]:
    """Read an achievements CSV and return {character_name: (total_quantity, total_points)}.

    "N/A" values are treated as -1 (not a hidden profile). A (0, 0) entry
    indicates a hidden Blizzard profile.

    Args:
        path: Filesystem path to the achievements CSV file.

    Returns:
        Mapping of character name to (total_quantity, total_points).
    """
    required = {"id", "name", "total_quantity", "total_points"}
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = required - fieldnames
        if missing:
            print(
                f"Error: {path} is missing columns: {sorted(missing)}",
                file=sys.stderr,
            )
            sys.exit(2)

        result: dict[str, tuple[int, int]] = {}
        for row in reader:
            raw_qty = row["total_quantity"]
            raw_pts = row["total_points"]
            qty = -1 if raw_qty.strip().upper() == "N/A" else int(raw_qty)
            pts = -1 if raw_pts.strip().upper() == "N/A" else int(raw_pts)
            result[row["name"]] = (qty, pts)
        return result


# ---------------------------------------------------------------------------
# Phase 3: Change detection
# ---------------------------------------------------------------------------


def compute_changes(
    old_mapping: dict[str, str],
    new_mapping: dict[str, str],
) -> list[tuple[str, str, str | None]]:
    """Return every character whose main assignment changed between snapshots.

    Characters present only in new_mapping (new guild members) are excluded;
    this function diagnoses regressions, not additions.

    Args:
        old_mapping: {name: main} from the old alts CSV.
        new_mapping: {name: main} from the new alts CSV.

    Returns:
        List of (character_name, old_main, new_main_or_None) tuples.
        new_main is None when the character is absent from the new snapshot.
    """
    changes: list[tuple[str, str, str | None]] = []
    for name, old_main in old_mapping.items():
        new_main = new_mapping.get(name)
        if new_main is None or new_main != old_main:
            changes.append((name, old_main, new_main))
    return changes


def build_group_sizes(mapping: dict[str, str]) -> dict[str, int]:
    """Return {main_name: member_count} from an alts mapping.

    Args:
        mapping: {character_name: main_name} from an alts CSV.

    Returns:
        Dict mapping each main name to the number of characters in its group.
    """
    sizes: dict[str, int] = {}
    for main in mapping.values():
        sizes[main] = sizes.get(main, 0) + 1
    return sizes


# ---------------------------------------------------------------------------
# Phase 4: Classification engine
# ---------------------------------------------------------------------------


def is_group_hidden(
    group_members: list[str],
    achievements: dict[str, tuple[int, int]],
) -> bool:
    """Return True if any group member has total_quantity == 0.

    Members absent from the achievements dict are treated as non-hidden.

    Args:
        group_members: All character names belonging to the group.
        achievements: {name: (total_quantity, total_points)} mapping.

    Returns:
        True if at least one member has a hidden Blizzard profile.
    """
    return any(
        achievements.get(member, (1, 1))[0] == 0 for member in group_members
    )


def classify_change(
    name: str,
    old_main: str,
    new_main: str | None,
    old_mapping: dict[str, str],
    new_mapping: dict[str, str],
    achievements: dict[str, tuple[int, int]],
    old_group_sizes: dict[str, int],
) -> tuple[str, str]:
    """Return (category, note) for a single changed assignment.

    Classification order (first match wins):
      1.  hidden-profile         — any old-group member has total_quantity == 0.
      2a. standalone-left        — old_main absent from new & group size == 1.
      2b. main-left-guild        — old_main absent from new & group size > 1.
      3.  member-left-guild      — character absent, but group leader remains.
      4.  main-selection-change   — group membership identical, different main.
      5.  group-absorbed         — old main demoted to alt in another group.
      6.  unknown                — none of the above; potential regression.

    Args:
        name: Character whose assignment changed.
        old_main: The main assigned in the old snapshot.
        new_main: The main assigned in the new snapshot, or None if absent.
        old_mapping: Full {name: main} mapping from the old snapshot.
        new_mapping: Full {name: main} mapping from the new snapshot.
        achievements: {name: (total_quantity, total_points)}.
        old_group_sizes: {main_name: member_count} from old snapshot.

    Returns:
        Tuple of (category_string, human_readable_note).
    """
    old_group_members = [c for c, m in old_mapping.items() if m == old_main]

    # Rule 1 — hidden profile
    if is_group_hidden(old_group_members, achievements):
        if len(old_group_members) > 1:
            return ("hidden-profile", "[entire group hidden]")
        return ("hidden-profile", "[profile hidden]")

    # Rule 2 — main left guild (split: standalone vs group leader)
    if old_main not in new_mapping:
        if old_group_sizes.get(old_main, 1) == 1:
            return ("standalone-left", "standalone character left guild")
        return ("main-left-guild", "old main absent from new snapshot")

    # Rule 2.5 — member left guild
    # The character itself is absent from the new snapshot, but their old group
    # leader is still present. The member departed; no algorithmic regression.
    if new_main is None:
        return ("member-left-guild", "character left guild; group leader still present")

    # Rule 3 — main-selection change
    effective_main = new_main if new_main is not None else old_main
    new_group_members = [c for c, m in new_mapping.items() if m == effective_main]
    if set(old_group_members) == set(new_group_members):
        return (
            "main-selection-change",
            f"group intact; main changed {old_main} -> {effective_main}",
        )

    # Rule 3.5 — group absorbed into a larger group
    # The old main character is now itself an alt of a different main, meaning
    # this group was merged with (or absorbed into) another player's group.
    # The algorithm correctly detected the new relationship; not a regression.
    if new_mapping.get(old_main, old_main) != old_main:
        absorbed_into = new_mapping[old_main]
        return (
            "group-absorbed",
            f"old group absorbed into {absorbed_into}'s group (old main demoted to alt)",
        )

    # Rule 4 — unknown
    return ("unknown", "no rule matched")


def classify_changes(
    changes: list[tuple[str, str, str | None]],
    old_mapping: dict[str, str],
    new_mapping: dict[str, str],
    achievements: dict[str, tuple[int, int]],
    old_group_sizes: dict[str, int],
) -> list[dict]:
    """Apply classify_change() to every entry and return Change dicts.

    Args:
        changes: Output of compute_changes().
        old_mapping: Full {name: main} from old snapshot.
        new_mapping: Full {name: main} from new snapshot.
        achievements: {name: (total_quantity, total_points)}.
        old_group_sizes: {main_name: member_count} from old snapshot.

    Returns:
        List of Change dicts with keys: name, old_main, new_main, category, note.
    """
    classified: list[dict] = []
    for name, old_main, new_main in changes:
        category, note = classify_change(
            name, old_main, new_main, old_mapping, new_mapping, achievements,
            old_group_sizes,
        )
        classified.append(
            {
                "name": name,
                "old_main": old_main,
                "new_main": new_main,
                "category": category,
                "note": note,
            }
        )
    return classified


# ---------------------------------------------------------------------------
# Phase 5: Report formatter
# ---------------------------------------------------------------------------


def print_report(
    changes: list[dict],
    old_path: str,
    new_path: str,
    achievements_path: str,
    old_total: int,
    new_total: int,
    ach_total: int,
) -> None:
    """Print the categorised regression report to stdout.

    Args:
        changes: Classified Change dicts from classify_changes().
        old_path: Path to the old alts CSV (for display).
        new_path: Path to the new alts CSV (for display).
        achievements_path: Path to the achievements CSV (for display).
        old_total: Number of characters in the old snapshot.
        new_total: Number of characters in the new snapshot.
        ach_total: Number of characters in the achievements file.
    """
    print("=== Alt Detection Regression Report ===")
    print(f"Old snapshot : {old_path}  ({old_total} rows)")
    print(f"New snapshot : {new_path}  ({new_total} rows)")
    print(f"Achievements : {achievements_path}  ({ach_total} rows)")
    print(f"Changed assignments : {len(changes)}")
    print()

    if not changes:
        print("No changes detected between snapshots.")
        return

    # Group by category in fixed order
    buckets: dict[str, list[dict]] = {cat: [] for cat in CATEGORY_ORDER}
    for change in changes:
        buckets[change["category"]].append(change)

    for category in CATEGORY_ORDER:
        bucket = buckets[category]
        print(f"--- {category} ({len(bucket)}) ---")
        if not bucket:
            print("  (none)")
        else:
            for c in bucket:
                new_main_str = c["new_main"] if c["new_main"] is not None else "<none>"
                name_col = c["name"].ljust(22)
                old_col = f"old-main={c['old_main']}".ljust(32)
                new_col = f"new-main={new_main_str}".ljust(30)
                print(f"  {name_col}  {old_col}  {new_col}  {c['note']}")
        print()

    # Summary
    print("=== Summary ===")
    for category in CATEGORY_ORDER:
        count = len(buckets[category])
        print(f"  {category:<26}: {count:>3}")
    print()

    unknown_count = len(buckets["unknown"])
    if unknown_count == 0:
        print("PASS — no unknown changes detected.")
    else:
        print(f"FAIL — {unknown_count} unknown change(s) detected.")


# ---------------------------------------------------------------------------
# Phase 6: main() — wire all phases
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: parse args, load data, compute changes, classify, report, exit."""
    parser = argparse.ArgumentParser(
        description=(
            "Diff two alt-detection CSV snapshots and classify every changed "
            "assignment. Both alts CSVs must be from the same guild slug."
        )
    )
    parser.add_argument(
        "--old",
        required=True,
        metavar="PATH",
        help="Path to the old alts CSV (baseline snapshot).",
    )
    parser.add_argument(
        "--new",
        required=True,
        metavar="PATH",
        help="Path to the new alts CSV (current snapshot).",
    )
    parser.add_argument(
        "--achievements",
        required=True,
        metavar="PATH",
        help="Path to the current achievements CSV.",
    )
    args = parser.parse_args()

    for label, path in [
        ("--old", args.old),
        ("--new", args.new),
        ("--achievements", args.achievements),
    ]:
        if not os.path.isfile(path):
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(2)

    old_mapping = load_alts(args.old)
    new_mapping = load_alts(args.new)
    achievements = load_achievements(args.achievements)

    old_total = len(old_mapping)
    new_total = len(new_mapping)
    ach_total = len(achievements)

    old_group_sizes = build_group_sizes(old_mapping)
    raw_changes = compute_changes(old_mapping, new_mapping)
    classified = classify_changes(
        raw_changes, old_mapping, new_mapping, achievements, old_group_sizes,
    )

    print_report(
        classified,
        args.old,
        args.new,
        args.achievements,
        old_total,
        new_total,
        ach_total,
    )

    unknown_count = sum(1 for c in classified if c["category"] == "unknown")
    sys.exit(1 if unknown_count > 0 else 0)


if __name__ == "__main__":
    main()
