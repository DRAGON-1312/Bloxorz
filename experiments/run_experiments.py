from __future__ import annotations

import argparse
import csv
import gc
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# File này nằm tại:
#     <project_root>/experiments/run_experiments.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_DIR = Path(__file__).resolve().parent

# Cho phép chạy cả:
#     python -m experiments.run_experiments
# và:
#     python experiments/run_experiments.py
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.game import Game
from core.level_loader import load_level
from solvers.astar import solve as solve_astar
from solvers.bfs import solve as solve_bfs
from solvers.ids import solve as solve_ids
from solvers.result import SearchResult
from solvers.ucs import solve as solve_ucs


DEFAULT_REPETITIONS = 5
DEFAULT_IDS_MAX_DEPTH = 120
DEFAULT_LEVELS_DIR = PROJECT_ROOT / "levels"

RAW_RESULTS_PATH = EXPERIMENTS_DIR / "results_raw.csv"
SUMMARY_RESULTS_PATH = EXPERIMENTS_DIR / "results_summary.csv"
ALGORITHM_SUMMARY_PATH = EXPERIMENTS_DIR / "algorithm_summary.csv"

ALGORITHM_ORDER = ("BFS", "IDS", "UCS", "A*")

CATEGORY_LABELS = {
    "basic_level": "Basic",
    "basic_levels": "Basic",
    "fragile_level": "Fragile",
    "fragile_levels": "Fragile",
    "bridge_switch_level": "Bridge/Switch",
    "bridge_switch_levels": "Bridge/Switch",
    "split_switch_level": "Split",
    "split_switch_levels": "Split",
    "combined_advanced_level": "Combined Advanced",
    "combined_advanced_levels": "Combined Advanced",
}

RAW_FIELDS = (
    "stage_number",
    "level",
    "level_name",
    "category",
    "level_path",
    "algorithm",
    "run",
    "execution_ok",
    "solved",
    "valid_path",
    "search_time_s",
    "memory_usage_bytes",
    "expanded_nodes",
    "solution_length",
    "solution_cost",
    "validated_cost",
    "path",
    "error",
)

SUMMARY_FIELDS = (
    "stage_number",
    "level",
    "level_name",
    "category",
    "algorithm",
    "runs",
    "successful_runs",
    "all_runs_ok",
    "solved_all",
    "paths_valid_all",
    "deterministic_consistent",
    "median_search_time_s",
    "mean_search_time_s",
    "stdev_search_time_s",
    "min_search_time_s",
    "max_search_time_s",
    "median_memory_usage_bytes",
    "mean_memory_usage_bytes",
    "expanded_nodes",
    "solution_length",
    "solution_cost",
    "path",
)

ALGORITHM_SUMMARY_FIELDS = (
    "algorithm",
    "tested_levels",
    "solved_levels",
    "valid_levels",
    "consistent_levels",
    "total_expanded_nodes",
    "median_search_time_ms",
    "median_memory_usage_kb",
    "mean_solution_length",
    "mean_solution_cost",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run BFS, IDS, UCS and A* on all Bloxorz levels, "
            "validate every path and export CSV results."
        )
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=DEFAULT_REPETITIONS,
        help=f"Runs per level and algorithm (default: {DEFAULT_REPETITIONS}).",
    )
    parser.add_argument(
        "--ids-max-depth",
        type=int,
        default=DEFAULT_IDS_MAX_DEPTH,
        help=f"Maximum IDS depth (default: {DEFAULT_IDS_MAX_DEPTH}).",
    )
    parser.add_argument(
        "--levels-dir",
        type=Path,
        default=DEFAULT_LEVELS_DIR,
        help="Directory containing stage_*.json files.",
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=list(ALGORITHM_ORDER),
        help="Subset of: BFS IDS UCS A* ASTAR.",
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        type=int,
        default=None,
        help="Optional stage numbers, for example: --stages 1 4 7 10",
    )

    return parser.parse_args()


def normalize_algorithm(name: str) -> str:
    normalized = name.strip().upper().replace(" ", "")

    aliases = {
        "BFS": "BFS",
        "IDS": "IDS",
        "UCS": "UCS",
        "A*": "A*",
        "ASTAR": "A*",
        "A-STAR": "A*",
        "A_STAR": "A*",
    }

    try:
        return aliases[normalized]
    except KeyError as error:
        raise ValueError(
            f"Unknown algorithm {name!r}. Use BFS, IDS, UCS or A*."
        ) from error


def normalize_algorithms(names: list[str]) -> list[str]:
    algorithms: list[str] = []

    for name in names:
        algorithm = normalize_algorithm(name)
        if algorithm not in algorithms:
            algorithms.append(algorithm)

    return sorted(algorithms, key=ALGORITHM_ORDER.index)


def get_stage_number(path: Path) -> int:
    match = re.search(r"stage_(\d+)", path.stem.lower())

    if match is None:
        raise ValueError(
            f"Level filename must contain stage_<number>: {path.name}"
        )

    return int(match.group(1))


def discover_levels(
    levels_dir: Path,
    selected_stages: list[int] | None,
) -> list[Path]:
    levels_dir = levels_dir.expanduser().resolve()

    if not levels_dir.is_dir():
        raise FileNotFoundError(f"Levels directory not found: {levels_dir}")

    paths = sorted(
        levels_dir.rglob("stage_*.json"),
        key=lambda path: (get_stage_number(path), str(path)),
    )

    if selected_stages is not None:
        selected = set(selected_stages)
        paths = [path for path in paths if get_stage_number(path) in selected]

        found = {get_stage_number(path) for path in paths}
        missing = sorted(selected - found)

        if missing:
            raise FileNotFoundError(
                "Missing stages: "
                + ", ".join(f"{stage:02d}" for stage in missing)
            )

    if not paths:
        raise FileNotFoundError(f"No stage_*.json found in: {levels_dir}")

    # Một stage number chỉ được xuất hiện đúng một lần.
    grouped: dict[int, list[Path]] = defaultdict(list)
    for path in paths:
        grouped[get_stage_number(path)].append(path)

    duplicates = {
        stage: stage_paths
        for stage, stage_paths in grouped.items()
        if len(stage_paths) > 1
    }

    if duplicates:
        details = "\n".join(
            f"Stage {stage:02d}: " + ", ".join(map(str, stage_paths))
            for stage, stage_paths in sorted(duplicates.items())
        )
        raise ValueError(f"Duplicate stage numbers found:\n{details}")

    return paths


def get_category(level_path: Path) -> str:
    folder = level_path.parent.name.lower()

    return CATEGORY_LABELS.get(
        folder,
        folder.replace("_", " ").title(),
    )


def format_level_path(level_path: Path) -> str:
    """Return a project-relative path when possible."""
    try:
        return level_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return level_path.as_posix()


def solve_game(
    algorithm: str,
    game: Game,
    ids_max_depth: int,
) -> SearchResult:
    if algorithm == "BFS":
        return solve_bfs(game)
    if algorithm == "IDS":
        return solve_ids(game, max_depth=ids_max_depth)
    if algorithm == "UCS":
        return solve_ucs(game)
    if algorithm == "A*":
        return solve_astar(game)

    raise RuntimeError(f"Unsupported algorithm: {algorithm}")


def validate_result(
    board,
    result: SearchResult,
) -> tuple[bool | None, int | float | None]:
    """
    Replay độc lập path bằng core.Game.

    Return:
        (True, cost): path hợp lệ và đến Goal.
        (None, None): solver báo không có lời giải.
    """
    path = result.path

    if path is None:
        if result.solution_length is not None:
            raise ValueError("path=None requires solution_length=None.")
        if result.solution_cost is not None:
            raise ValueError("path=None requires solution_cost=None.")

        return None, None

    if result.solution_length != len(path):
        raise ValueError(
            "solution_length does not equal len(path): "
            f"{result.solution_length} != {len(path)}"
        )

    game = Game(board)
    current_state = game.initial_state
    calculated_cost: int | float = 0

    for step_number, action in enumerate(path, start=1):
        next_state = game.apply_move(current_state, action)

        if next_state is None:
            raise ValueError(
                f"Invalid path at step {step_number}: action={action!r}"
            )

        calculated_cost += game.get_move_cost(
            current_state=current_state,
            next_state=next_state,
            action=action,
        )
        current_state = next_state

    if not game.is_goal_state(current_state):
        raise ValueError("Returned path does not reach the Goal.")

    if (
        result.solution_cost is not None
        and result.solution_cost != calculated_cost
    ):
        raise ValueError(
            "solution_cost differs from replayed cost: "
            f"{result.solution_cost} != {calculated_cost}"
        )

    return True, calculated_cost


def run_once(
    *,
    level_path: Path,
    board,
    algorithm: str,
    run_number: int,
    ids_max_depth: int,
) -> dict[str, Any]:
    stage_number = get_stage_number(level_path)

    row: dict[str, Any] = {
        "stage_number": stage_number,
        "level": f"Stage {stage_number:02d}",
        "level_name": board.name,
        "category": get_category(level_path),
        "level_path": format_level_path(level_path),
        "algorithm": algorithm,
        "run": run_number,
        "execution_ok": False,
        "solved": False,
        "valid_path": None,
        "search_time_s": None,
        "memory_usage_bytes": None,
        "expanded_nodes": None,
        "solution_length": None,
        "solution_cost": None,
        "validated_cost": None,
        "path": "",
        "error": "",
    }

    try:
        # Giảm ảnh hưởng object rác còn lại từ lần chạy trước.
        gc.collect()

        result = solve_game(
            algorithm=algorithm,
            game=Game(board),
            ids_max_depth=ids_max_depth,
        )

        valid_path, validated_cost = validate_result(board, result)

        row.update(
            {
                "execution_ok": True,
                "solved": result.path is not None,
                "valid_path": valid_path,
                "search_time_s": result.search_time,
                "memory_usage_bytes": result.memory_usage,
                "expanded_nodes": result.expanded_nodes,
                "solution_length": result.solution_length,
                "solution_cost": result.solution_cost,
                "validated_cost": validated_cost,
                "path": (
                    json.dumps(result.path)
                    if result.path is not None
                    else ""
                ),
            }
        )

    except Exception as error:
        row["error"] = f"{type(error).__name__}: {error}"

    return row


def write_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def initialize_raw_csv() -> None:
    write_csv(RAW_RESULTS_PATH, RAW_FIELDS, [])


def append_raw_row(row: dict[str, Any]) -> None:
    # Ghi ngay sau mỗi run để không mất dữ liệu nếu IDS chạy lâu
    # hoặc người dùng dừng chương trình giữa chừng.
    with RAW_RESULTS_PATH.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RAW_FIELDS)
        writer.writerow(row)


def safe_mean(values: list[float | int]) -> float | None:
    return statistics.mean(values) if values else None


def safe_median(values: list[float | int]) -> float | None:
    return statistics.median(values) if values else None


def safe_stdev(values: list[float | int]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def create_summary_rows(
    raw_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)

    for row in raw_rows:
        groups[(int(row["stage_number"]), str(row["algorithm"]))].append(row)

    summaries: list[dict[str, Any]] = []

    for (stage_number, algorithm), rows in groups.items():
        successful = [row for row in rows if row["execution_ok"] is True]

        times = [
            float(row["search_time_s"])
            for row in successful
            if row["search_time_s"] is not None
        ]
        memories = [
            int(row["memory_usage_bytes"])
            for row in successful
            if row["memory_usage_bytes"] is not None
        ]

        first = successful[0] if successful else rows[0]
        all_runs_ok = len(successful) == len(rows)
        solved_all = all_runs_ok and all(row["solved"] is True for row in successful)
        paths_valid_all = solved_all and all(
            row["valid_path"] is True for row in successful
        )

        deterministic_keys = (
            "solved",
            "expanded_nodes",
            "solution_length",
            "solution_cost",
            "path",
        )
        deterministic_consistent = all_runs_ok and all(
            len({row[key] for row in successful}) <= 1
            for key in deterministic_keys
        )

        summaries.append(
            {
                "stage_number": stage_number,
                "level": first["level"],
                "level_name": first["level_name"],
                "category": first["category"],
                "algorithm": algorithm,
                "runs": len(rows),
                "successful_runs": len(successful),
                "all_runs_ok": all_runs_ok,
                "solved_all": solved_all,
                "paths_valid_all": paths_valid_all,
                "deterministic_consistent": deterministic_consistent,
                "median_search_time_s": safe_median(times),
                "mean_search_time_s": safe_mean(times),
                "stdev_search_time_s": safe_stdev(times),
                "min_search_time_s": min(times) if times else None,
                "max_search_time_s": max(times) if times else None,
                "median_memory_usage_bytes": safe_median(memories),
                "mean_memory_usage_bytes": safe_mean(memories),
                "expanded_nodes": first["expanded_nodes"],
                "solution_length": first["solution_length"],
                "solution_cost": first["solution_cost"],
                "path": first["path"],
            }
        )

    summaries.sort(
        key=lambda row: (
            int(row["stage_number"]),
            ALGORITHM_ORDER.index(str(row["algorithm"])),
        )
    )

    return summaries


def create_algorithm_summary_rows(
    summary_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in summary_rows:
        groups[str(row["algorithm"])].append(row)

    output: list[dict[str, Any]] = []

    for algorithm in ALGORITHM_ORDER:
        rows = groups.get(algorithm, [])
        if not rows:
            continue

        times_ms = [
            float(row["median_search_time_s"]) * 1000
            for row in rows
            if row["median_search_time_s"] is not None
        ]
        memories_kb = [
            float(row["median_memory_usage_bytes"]) / 1024
            for row in rows
            if row["median_memory_usage_bytes"] is not None
        ]
        lengths = [
            int(row["solution_length"])
            for row in rows
            if row["solution_length"] is not None
        ]
        costs = [
            float(row["solution_cost"])
            for row in rows
            if row["solution_cost"] is not None
        ]
        expanded = [
            int(row["expanded_nodes"])
            for row in rows
            if row["expanded_nodes"] is not None
        ]

        output.append(
            {
                "algorithm": algorithm,
                "tested_levels": len(rows),
                "solved_levels": sum(bool(row["solved_all"]) for row in rows),
                "valid_levels": sum(bool(row["paths_valid_all"]) for row in rows),
                "consistent_levels": sum(
                    bool(row["deterministic_consistent"]) for row in rows
                ),
                "total_expanded_nodes": sum(expanded),
                "median_search_time_ms": safe_median(times_ms),
                "median_memory_usage_kb": safe_median(memories_kb),
                "mean_solution_length": safe_mean(lengths),
                "mean_solution_cost": safe_mean(costs),
            }
        )

    return output


def print_run(row: dict[str, Any]) -> None:
    prefix = (
        f"{row['level']} | {row['algorithm']:>3} | "
        f"run {row['run']}"
    )

    if not row["execution_ok"]:
        print(f"{prefix} | ERROR | {row['error']}", flush=True)
        return

    if not row["solved"]:
        print(
            f"{prefix} | no solution | "
            f"time={row['search_time_s']:.6f}s | "
            f"expanded={row['expanded_nodes']}",
            flush=True,
        )
        return

    memory_kb = float(row["memory_usage_bytes"]) / 1024

    print(
        f"{prefix} | solved | "
        f"time={row['search_time_s']:.6f}s | "
        f"memory={memory_kb:.2f}KB | "
        f"expanded={row['expanded_nodes']} | "
        f"length={row['solution_length']} | "
        f"cost={row['solution_cost']}",
        flush=True,
    )


def main() -> int:
    args = parse_arguments()

    if args.repetitions <= 0:
        raise ValueError("repetitions must be greater than 0.")
    if args.ids_max_depth < 0:
        raise ValueError("ids-max-depth must be at least 0.")

    algorithms = normalize_algorithms(args.algorithms)
    level_paths = discover_levels(args.levels_dir, args.stages)

    expected_runs = len(level_paths) * len(algorithms) * args.repetitions

    print("=" * 72)
    print("BLOXORZ SOLVER EXPERIMENTS")
    print("=" * 72)
    print(
        "Levels: "
        + ", ".join(
            f"Stage {get_stage_number(path):02d}" for path in level_paths
        )
    )
    print("Algorithms: " + ", ".join(algorithms))
    print(f"Repetitions: {args.repetitions}")
    print(f"Expected runs: {expected_runs}")
    print("=" * 72)

    initialize_raw_csv()
    raw_rows: list[dict[str, Any]] = []
    interrupted = False

    try:
        for level_path in level_paths:
            board = load_level(str(level_path))
            stage_number = get_stage_number(level_path)

            print("\n" + "-" * 72)
            print(
                f"Stage {stage_number:02d}: {board.name} "
                f"[{get_category(level_path)}]"
            )
            print(f"File: {format_level_path(level_path)}")
            print("-" * 72)

            for algorithm in algorithms:
                for run_number in range(1, args.repetitions + 1):
                    row = run_once(
                        level_path=level_path,
                        board=board,
                        algorithm=algorithm,
                        run_number=run_number,
                        ids_max_depth=args.ids_max_depth,
                    )

                    raw_rows.append(row)
                    append_raw_row(row)
                    print_run(row)

    except KeyboardInterrupt:
        interrupted = True
        print(
            "\nExperiment interrupted. Partial results_raw.csv was preserved.",
            file=sys.stderr,
        )

    summaries = create_summary_rows(raw_rows)
    algorithm_summaries = create_algorithm_summary_rows(summaries)

    write_csv(SUMMARY_RESULTS_PATH, SUMMARY_FIELDS, summaries)
    write_csv(
        ALGORITHM_SUMMARY_PATH,
        ALGORITHM_SUMMARY_FIELDS,
        algorithm_summaries,
    )

    errors = sum(not bool(row["execution_ok"]) for row in raw_rows)

    print("\n" + "=" * 72)
    print("EXPERIMENT FINISHED")
    print("=" * 72)
    print(f"Completed runs: {len(raw_rows)}/{expected_runs}")
    print(f"Errors: {errors}")
    print(f"Raw results: {RAW_RESULTS_PATH}")
    print(f"Summary results: {SUMMARY_RESULTS_PATH}")
    print(f"Algorithm summary: {ALGORITHM_SUMMARY_PATH}")

    if interrupted:
        return 130
    if errors:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())