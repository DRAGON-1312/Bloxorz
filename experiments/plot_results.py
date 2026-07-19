from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------
# Có thể chạy bằng:
#
#     python -m experiments.plot_results
#     python experiments/plot_results.py
# ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import matplotlib.pyplot as plt


EXPERIMENTS_DIR = Path(__file__).resolve().parent
DEFAULT_SUMMARY_PATH = EXPERIMENTS_DIR / "results_summary.csv"
DEFAULT_RAW_PATH = EXPERIMENTS_DIR / "results_raw.csv"
DEFAULT_OUTPUT_DIR = EXPERIMENTS_DIR / "plots"

ALGORITHM_ORDER = (
    "BFS",
    "IDS",
    "UCS",
    "A*",
)

BAR_WIDTH = 0.19
FIGURE_SIZE = (12, 6.8)
REPORT_DPI = 300


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate report-ready experiment charts from "
            "results_summary.csv and results_raw.csv."
        )
    )

    parser.add_argument(
        "--summary-input",
        type=Path,
        default=DEFAULT_SUMMARY_PATH,
        help=(
            "Path to results_summary.csv "
            f"(default: {DEFAULT_SUMMARY_PATH})"
        ),
    )

    parser.add_argument(
        "--raw-input",
        type=Path,
        default=DEFAULT_RAW_PATH,
        help=(
            "Path to results_raw.csv "
            f"(default: {DEFAULT_RAW_PATH})"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Directory where charts and report tables are saved "
            f"(default: {DEFAULT_OUTPUT_DIR})"
        ),
    )

    return parser.parse_args()


def read_csv_rows(
    csv_path: Path
) -> list[dict[str, str]]:
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Cannot find CSV file: {csv_path}"
        )

    with csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        rows = list(
            csv.DictReader(csv_file)
        )

    if not rows:
        raise ValueError(
            f"CSV file is empty: {csv_path}"
        )

    return rows


def to_int(
    value: str | None
) -> int | None:
    if value is None:
        return None

    value = value.strip()

    if value in {"", "--"}:
        return None

    return int(float(value))


def to_float(
    value: str | None
) -> float | None:
    if value is None:
        return None

    value = value.strip()

    if value in {"", "--"}:
        return None

    return float(value)


def to_bool(
    value: str | None
) -> bool:
    if value is None:
        return False

    return value.strip().lower() == "true"


def normalize_summary_rows(
    rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []

    for row in rows:
        normalized_rows.append(
            {
                "stage_number": to_int(
                    row.get("stage_number")
                ),
                "level": row.get("level", ""),
                "level_name": row.get(
                    "level_name",
                    "",
                ),
                "category": row.get(
                    "category",
                    "",
                ),
                "algorithm": row.get(
                    "algorithm",
                    "",
                ),
                "runs": to_int(
                    row.get("runs")
                ),
                "successful_runs": to_int(
                    row.get("successful_runs")
                ),
                "all_runs_ok": to_bool(
                    row.get("all_runs_ok")
                ),
                "solved_all": to_bool(
                    row.get("solved_all")
                ),
                "paths_valid_all": to_bool(
                    row.get("paths_valid_all")
                ),
                "deterministic_consistent": to_bool(
                    row.get(
                        "deterministic_consistent"
                    )
                ),
                "median_search_time_s": to_float(
                    row.get(
                        "median_search_time_s"
                    )
                ),
                "mean_search_time_s": to_float(
                    row.get(
                        "mean_search_time_s"
                    )
                ),
                "stdev_search_time_s": to_float(
                    row.get(
                        "stdev_search_time_s"
                    )
                ),
                "min_search_time_s": to_float(
                    row.get(
                        "min_search_time_s"
                    )
                ),
                "max_search_time_s": to_float(
                    row.get(
                        "max_search_time_s"
                    )
                ),
                "median_memory_usage_bytes": to_float(
                    row.get(
                        "median_memory_usage_bytes"
                    )
                ),
                "mean_memory_usage_bytes": to_float(
                    row.get(
                        "mean_memory_usage_bytes"
                    )
                ),
                "expanded_nodes": to_int(
                    row.get("expanded_nodes")
                ),
                "solution_length": to_int(
                    row.get("solution_length")
                ),
                "solution_cost": to_float(
                    row.get("solution_cost")
                ),
                "path": row.get(
                    "path",
                    "",
                ),
            }
        )

    return normalized_rows


def normalize_raw_rows(
    rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []

    for row in rows:
        normalized_rows.append(
            {
                "stage_number": to_int(
                    row.get("stage_number")
                ),
                "level": row.get(
                    "level",
                    "",
                ),
                "algorithm": row.get(
                    "algorithm",
                    "",
                ),
                "run": to_int(
                    row.get("run")
                ),
                "execution_ok": to_bool(
                    row.get("execution_ok")
                ),
                "solved": to_bool(
                    row.get("solved")
                ),
                "valid_path": (
                    None
                    if row.get("valid_path", "").strip() == ""
                    else to_bool(
                        row.get("valid_path")
                    )
                ),
                "search_time_s": to_float(
                    row.get("search_time_s")
                ),
                "memory_usage_bytes": to_float(
                    row.get("memory_usage_bytes")
                ),
            }
        )

    return normalized_rows


def validate_summary_rows(
    rows: list[dict[str, Any]]
) -> None:
    failed_rows = [
        row
        for row in rows
        if not (
            row["all_runs_ok"]
            and row["solved_all"]
            and row["paths_valid_all"]
        )
    ]

    if not failed_rows:
        return

    print(
        "WARNING: Some summary rows are not fully successful. "
        "Numeric values will still be plotted when available.\n"
    )

    for row in failed_rows:
        print(
            f"  - {row['level']} | {row['algorithm']} | "
            f"all_runs_ok={row['all_runs_ok']} | "
            f"solved_all={row['solved_all']} | "
            f"paths_valid_all={row['paths_valid_all']}"
        )

    print()


def ensure_output_dir(
    output_dir: Path
) -> None:
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


def get_stage_numbers(
    rows: list[dict[str, Any]]
) -> list[int]:
    stage_numbers = sorted(
        {
            int(row["stage_number"])
            for row in rows
            if row["stage_number"] is not None
        }
    )

    if not stage_numbers:
        raise ValueError(
            "No valid stage numbers were found."
        )

    return stage_numbers


def get_stage_labels(
    stage_numbers: list[int]
) -> list[str]:
    return [
        f"Stage {stage_number:02d}"
        for stage_number in stage_numbers
    ]


def get_algorithm_offset(
    algorithm_index: int
) -> float:
    algorithm_count = len(
        ALGORITHM_ORDER
    )

    return (
        algorithm_index
        - (algorithm_count - 1) / 2
    ) * BAR_WIDTH


def create_summary_lookup(
    rows: list[dict[str, Any]]
) -> dict[tuple[int, str], dict[str, Any]]:
    return {
        (
            int(row["stage_number"]),
            str(row["algorithm"]),
        ): row
        for row in rows
        if row["stage_number"] is not None
    }


def aggregate_raw_metric(
    raw_rows: list[dict[str, Any]],
    metric_key: str,
    *,
    transform,
) -> dict[
    tuple[int, str],
    tuple[float, float, float],
]:
    grouped_values: dict[
        tuple[int, str],
        list[float],
    ] = defaultdict(list)

    for row in raw_rows:
        if not row["execution_ok"]:
            continue

        stage_number = row["stage_number"]
        algorithm = row["algorithm"]
        value = row.get(metric_key)

        if (
            stage_number is None
            or algorithm not in ALGORITHM_ORDER
            or value is None
        ):
            continue

        transformed_value = float(
            transform(value)
        )

        if transformed_value <= 0:
            # Log-scale charts require positive values.
            continue

        grouped_values[
            (
                int(stage_number),
                str(algorithm),
            )
        ].append(
            transformed_value
        )

    statistics_by_case: dict[
        tuple[int, str],
        tuple[float, float, float],
    ] = {}

    for key, values in grouped_values.items():
        statistics_by_case[key] = (
            float(statistics.median(values)),
            float(min(values)),
            float(max(values)),
        )

    return statistics_by_case


def configure_common_axes(
    *,
    stage_numbers: list[int],
    ylabel: str,
    title: str,
    log_scale: bool,
) -> None:
    x_positions = list(
        range(len(stage_numbers))
    )

    plt.xticks(
        x_positions,
        get_stage_labels(stage_numbers),
        rotation=35,
        ha="right",
    )

    plt.xlabel("Benchmark Level")
    plt.ylabel(ylabel)
    plt.title(title)

    if log_scale:
        plt.yscale("log")
        plt.grid(
            True,
            which="both",
            alpha=0.35,
        )
    else:
        plt.grid(
            True,
            axis="y",
            alpha=0.35,
        )

    plt.legend()
    plt.tight_layout()


def plot_grouped_bar_chart(
    *,
    summary_rows: list[dict[str, Any]],
    metric_key: str,
    title: str,
    ylabel: str,
    output_path: Path,
    transform=lambda value: value,
    log_scale: bool = False,
) -> None:
    """
    Dùng grouped bar thay vì line chart vì các Stage là những benchmark
    độc lập, không phải một chuỗi thời gian liên tục.

    Điều này tránh tạo cảm giác Stage 08 tăng rồi Stage 09 "tụt",
    trong khi bản chất chỉ là Stage 08 có không gian tìm kiếm khó hơn.
    """
    stage_numbers = get_stage_numbers(
        summary_rows
    )

    lookup = create_summary_lookup(
        summary_rows
    )

    base_positions = list(
        range(len(stage_numbers))
    )

    plt.figure(
        figsize=FIGURE_SIZE
    )

    for algorithm_index, algorithm in enumerate(
        ALGORITHM_ORDER
    ):
        x_positions: list[float] = []
        values: list[float] = []

        for stage_index, stage_number in enumerate(
            stage_numbers
        ):
            row = lookup.get(
                (stage_number, algorithm)
            )

            if row is None:
                continue

            value = row.get(metric_key)

            if value is None:
                continue

            plotted_value = float(
                transform(value)
            )

            if log_scale and plotted_value <= 0:
                continue

            x_positions.append(
                base_positions[stage_index]
                + get_algorithm_offset(
                    algorithm_index
                )
            )

            values.append(
                plotted_value
            )

        if x_positions:
            plt.bar(
                x_positions,
                values,
                width=BAR_WIDTH,
                label=algorithm,
            )

    configure_common_axes(
        stage_numbers=stage_numbers,
        ylabel=ylabel,
        title=title,
        log_scale=log_scale,
    )

    plt.savefig(
        output_path,
        dpi=REPORT_DPI,
        bbox_inches="tight",
    )
    plt.close()


def plot_grouped_bar_with_range(
    *,
    summary_rows: list[dict[str, Any]],
    raw_statistics: dict[
        tuple[int, str],
        tuple[float, float, float],
    ],
    title: str,
    ylabel: str,
    output_path: Path,
    log_scale: bool,
) -> None:
    """
    Thanh biểu diễn median.
    Error bar bất đối xứng biểu diễn khoảng Min-Max.

    Error bar rõ hơn vùng tô mờ khi các benchmark có độ lớn chênh lệch
    nhiều bậc, đặc biệt ở Stage 08.
    """
    stage_numbers = get_stage_numbers(
        summary_rows
    )

    base_positions = list(
        range(len(stage_numbers))
    )

    plt.figure(
        figsize=FIGURE_SIZE
    )

    for algorithm_index, algorithm in enumerate(
        ALGORITHM_ORDER
    ):
        x_positions: list[float] = []
        medians: list[float] = []
        lower_errors: list[float] = []
        upper_errors: list[float] = []

        for stage_index, stage_number in enumerate(
            stage_numbers
        ):
            statistics_tuple = raw_statistics.get(
                (stage_number, algorithm)
            )

            if statistics_tuple is None:
                continue

            median_value, min_value, max_value = (
                statistics_tuple
            )

            x_positions.append(
                base_positions[stage_index]
                + get_algorithm_offset(
                    algorithm_index
                )
            )

            medians.append(
                median_value
            )
            lower_errors.append(
                median_value - min_value
            )
            upper_errors.append(
                max_value - median_value
            )

        if not x_positions:
            continue

        plt.bar(
            x_positions,
            medians,
            width=BAR_WIDTH,
            label=algorithm,
            yerr=[
                lower_errors,
                upper_errors,
            ],
            capsize=3,
            error_kw={
                "elinewidth": 1,
                "capthick": 1,
            },
        )

    configure_common_axes(
        stage_numbers=stage_numbers,
        ylabel=ylabel,
        title=title,
        log_scale=log_scale,
    )

    plt.savefig(
        output_path,
        dpi=REPORT_DPI,
        bbox_inches="tight",
    )
    plt.close()



def draw_grouped_bars_on_axes(
    *,
    axes,
    summary_rows: list[dict[str, Any]],
    metric_key: str,
    title: str,
    ylabel: str,
) -> None:
    """
    Draw one grouped-bar comparison on an existing Matplotlib Axes.

    This helper is used to place Solution Length and Solution Cost
    side by side in one report-ready figure without using a dual y-axis.
    """
    stage_numbers = get_stage_numbers(
        summary_rows
    )

    lookup = create_summary_lookup(
        summary_rows
    )

    base_positions = list(
        range(len(stage_numbers))
    )

    for algorithm_index, algorithm in enumerate(
        ALGORITHM_ORDER
    ):
        x_positions: list[float] = []
        values: list[float] = []

        for stage_index, stage_number in enumerate(
            stage_numbers
        ):
            row = lookup.get(
                (stage_number, algorithm)
            )

            if row is None:
                continue

            value = row.get(
                metric_key
            )

            if value is None:
                continue

            x_positions.append(
                base_positions[stage_index]
                + get_algorithm_offset(
                    algorithm_index
                )
            )

            values.append(
                float(value)
            )

        if x_positions:
            axes.bar(
                x_positions,
                values,
                width=BAR_WIDTH,
                label=algorithm,
            )

    axes.set_xticks(
        base_positions
    )

    axes.set_xticklabels(
        get_stage_labels(
            stage_numbers
        ),
        rotation=35,
        ha="right",
    )

    axes.set_xlabel(
        "Benchmark Level"
    )

    axes.set_ylabel(
        ylabel
    )

    axes.set_title(
        title
    )

    axes.grid(
        True,
        axis="y",
        alpha=0.35,
    )


def plot_solution_quality_comparison(
    *,
    summary_rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """
    Combine Solution Length and Solution Cost into one figure.

    Two side-by-side panels are clearer and less misleading than a
    dual-y-axis chart because each metric keeps its own independent scale.
    """
    figure, axes = plt.subplots(
        1,
        2,
        figsize=(15.5, 6.8),
    )

    draw_grouped_bars_on_axes(
        axes=axes[0],
        summary_rows=summary_rows,
        metric_key="solution_length",
        title="Solution Length",
        ylabel="Solution Length (moves)",
    )

    draw_grouped_bars_on_axes(
        axes=axes[1],
        summary_rows=summary_rows,
        metric_key="solution_cost",
        title="Solution Cost",
        ylabel="Solution Cost",
    )

    handles, labels = axes[0].get_legend_handles_labels()

    figure.legend(
        handles,
        labels,
        loc="upper center",
        ncol=len(ALGORITHM_ORDER),
        bbox_to_anchor=(0.5, 0.99),
    )

    figure.suptitle(
        "Solution Quality across Benchmark Levels",
        y=1.04,
    )

    figure.tight_layout(
        rect=(0, 0, 1, 0.93)
    )

    figure.savefig(
        output_path,
        dpi=REPORT_DPI,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )



def create_pivot_table_csv(
    *,
    rows: list[dict[str, Any]],
    metric_key: str,
    output_path: Path,
    value_formatter,
) -> None:
    stage_numbers = get_stage_numbers(
        rows
    )

    lookup = create_summary_lookup(
        rows
    )

    fieldnames = [
        "level",
        *ALGORITHM_ORDER,
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for stage_number in stage_numbers:
            output_row: dict[str, Any] = {
                "level": f"Stage {stage_number:02d}"
            }

            for algorithm in ALGORITHM_ORDER:
                row = lookup.get(
                    (stage_number, algorithm)
                )

                if (
                    row is None
                    or row.get(metric_key) is None
                ):
                    output_row[algorithm] = ""
                else:
                    output_row[algorithm] = (
                        value_formatter(
                            row[metric_key]
                        )
                    )

            writer.writerow(
                output_row
            )


def create_stability_table(
    *,
    statistics_by_case: dict[
        tuple[int, str],
        tuple[float, float, float],
    ],
    output_path: Path,
    value_name: str,
    decimal_places: int = 6,
) -> None:
    fieldnames = (
        "level",
        "algorithm",
        f"median_{value_name}",
        f"min_{value_name}",
        f"max_{value_name}",
        f"range_{value_name}",
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for (
            stage_number,
            algorithm,
        ), (
            median_value,
            min_value,
            max_value,
        ) in sorted(
            statistics_by_case.items(),
            key=lambda item: (
                item[0][0],
                ALGORITHM_ORDER.index(
                    item[0][1]
                ),
            ),
        ):
            writer.writerow(
                {
                    "level": (
                        f"Stage {stage_number:02d}"
                    ),
                    "algorithm": algorithm,
                    f"median_{value_name}": (
                        f"{median_value:.{decimal_places}f}"
                    ),
                    f"min_{value_name}": (
                        f"{min_value:.{decimal_places}f}"
                    ),
                    f"max_{value_name}": (
                        f"{max_value:.{decimal_places}f}"
                    ),
                    f"range_{value_name}": (
                        f"{max_value - min_value:.{decimal_places}f}"
                    ),
                }
            )


def create_report_summary_txt(
    *,
    rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    by_algorithm: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in rows:
        by_algorithm[
            row["algorithm"]
        ].append(
            row
        )

    lines = [
        "BLOXORZ EXPERIMENT SUMMARY",
        "=" * 32,
        "",
    ]

    for algorithm in ALGORITHM_ORDER:
        algorithm_rows = by_algorithm.get(
            algorithm,
            [],
        )

        if not algorithm_rows:
            continue

        time_values_ms = [
            row["median_search_time_s"] * 1000
            for row in algorithm_rows
            if row["median_search_time_s"] is not None
        ]

        memory_values_kb = [
            row["median_memory_usage_bytes"] / 1024
            for row in algorithm_rows
            if row["median_memory_usage_bytes"] is not None
        ]

        expanded_values = [
            row["expanded_nodes"]
            for row in algorithm_rows
            if row["expanded_nodes"] is not None
        ]

        solution_lengths = [
            row["solution_length"]
            for row in algorithm_rows
            if row["solution_length"] is not None
        ]

        solution_costs = [
            row["solution_cost"]
            for row in algorithm_rows
            if row["solution_cost"] is not None
        ]

        lines.extend(
            [
                f"[{algorithm}]",
                (
                    f"- tested levels: "
                    f"{len(algorithm_rows)}"
                ),
                (
                    "- median time across levels (ms): "
                    + (
                        f"{statistics.median(time_values_ms):.3f}"
                        if time_values_ms
                        else "--"
                    )
                ),
                (
                    "- median memory across levels (KB): "
                    + (
                        f"{statistics.median(memory_values_kb):.3f}"
                        if memory_values_kb
                        else "--"
                    )
                ),
                (
                    "- total expanded nodes: "
                    + (
                        str(sum(expanded_values))
                        if expanded_values
                        else "--"
                    )
                ),
                (
                    "- mean solution length: "
                    + (
                        f"{statistics.mean(solution_lengths):.3f}"
                        if solution_lengths
                        else "--"
                    )
                ),
                (
                    "- mean solution cost: "
                    + (
                        f"{statistics.mean(solution_costs):.3f}"
                        if solution_costs
                        else "--"
                    )
                ),
                "",
            ]
        )

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def create_figure_notes(
    output_path: Path
) -> None:
    notes = """REPORT FIGURE NOTES

1. Expanded Nodes, Search Time and Peak Memory use logarithmic y-axes
   because their values differ by several orders of magnitude.

2. The stages are independent benchmark instances, not a continuous
   time series. Grouped bar charts are therefore used instead of line
   charts. A large value at Stage 08 followed by a smaller Stage 09 value
   means Stage 08 has a more difficult search space; it is not a plotting
   error and does not imply that performance should change monotonically.

3. Search Time and Peak Memory:
   - bar height = median of repeated runs;
   - lower and upper error bars = minimum and maximum observed values.

4. Expanded Nodes, Solution Length and Solution Cost are deterministic
   metrics, so Min-Max ranges are not necessary when repeated runs return
   the same solution and node count.

5. Solution Length and Solution Cost are shown as two side-by-side panels
   in one figure. This makes it easier to compare the trade-off between
   path length and total path cost while avoiding the visual ambiguity of
   a dual-y-axis chart.
"""

    output_path.write_text(
        notes,
        encoding="utf-8",
    )


def main() -> int:
    arguments = parse_arguments()

    summary_path = (
        arguments.summary_input
        .expanduser()
        .resolve()
    )

    raw_path = (
        arguments.raw_input
        .expanduser()
        .resolve()
    )

    output_dir = (
        arguments.output_dir
        .expanduser()
        .resolve()
    )

    ensure_output_dir(
        output_dir
    )

    summary_rows = normalize_summary_rows(
        read_csv_rows(
            summary_path
        )
    )

    raw_rows = normalize_raw_rows(
        read_csv_rows(
            raw_path
        )
    )

    validate_summary_rows(
        summary_rows
    )

    search_time_statistics = aggregate_raw_metric(
        raw_rows,
        "search_time_s",
        transform=lambda value: value * 1000,
    )

    memory_statistics = aggregate_raw_metric(
        raw_rows,
        "memory_usage_bytes",
        transform=lambda value: value / 1024,
    )

    # -----------------------------------------------------------------
    # Report-ready figures
    # -----------------------------------------------------------------

    # 1) Expanded nodes:
    # grouped bars + logarithmic scale.
    plot_grouped_bar_chart(
        summary_rows=summary_rows,
        metric_key="expanded_nodes",
        title="Expanded Nodes across Benchmark Levels",
        ylabel="Expanded Nodes (log scale)",
        output_path=(
            output_dir
            / "expanded_nodes_by_level.png"
        ),
        log_scale=True,
    )

    # 2) Search time:
    # median bars + Min-Max error bars + logarithmic scale.
    plot_grouped_bar_with_range(
        summary_rows=summary_rows,
        raw_statistics=search_time_statistics,
        title=(
            "Search Time across Benchmark Levels "
            "(Median with Min-Max Range)"
        ),
        ylabel="Search Time (ms, log scale)",
        output_path=(
            output_dir
            / "search_time_by_level.png"
        ),
        log_scale=True,
    )

    # 3) Peak memory:
    # median bars + Min-Max error bars + logarithmic scale.
    plot_grouped_bar_with_range(
        summary_rows=summary_rows,
        raw_statistics=memory_statistics,
        title=(
            "Peak Memory Usage across Benchmark Levels "
            "(Median with Min-Max Range)"
        ),
        ylabel="Peak Memory Usage (KB, log scale)",
        output_path=(
            output_dir
            / "memory_usage_by_level.png"
        ),
        log_scale=True,
    )

    # 4) Solution quality:
    # Solution Length and Solution Cost are placed side by side in one
    # figure so the reader can directly compare "shorter path" and
    # "lower total cost" without the ambiguity of a dual y-axis.
    plot_solution_quality_comparison(
        summary_rows=summary_rows,
        output_path=(
            output_dir
            / "solution_quality_comparison.png"
        ),
    )

    # -----------------------------------------------------------------
    # CSV tables for the report
    # -----------------------------------------------------------------

    create_pivot_table_csv(
        rows=summary_rows,
        metric_key="expanded_nodes",
        output_path=(
            output_dir
            / "expanded_nodes_table.csv"
        ),
        value_formatter=lambda value: str(value),
    )

    create_pivot_table_csv(
        rows=summary_rows,
        metric_key="median_search_time_s",
        output_path=(
            output_dir
            / "search_time_table_ms.csv"
        ),
        value_formatter=(
            lambda value: f"{value * 1000:.6f}"
        ),
    )

    create_pivot_table_csv(
        rows=summary_rows,
        metric_key="median_memory_usage_bytes",
        output_path=(
            output_dir
            / "memory_usage_table_kb.csv"
        ),
        value_formatter=(
            lambda value: f"{value / 1024:.6f}"
        ),
    )

    create_pivot_table_csv(
        rows=summary_rows,
        metric_key="solution_length",
        output_path=(
            output_dir
            / "solution_length_table.csv"
        ),
        value_formatter=lambda value: str(value),
    )

    create_pivot_table_csv(
        rows=summary_rows,
        metric_key="solution_cost",
        output_path=(
            output_dir
            / "solution_cost_table.csv"
        ),
        value_formatter=(
            lambda value: f"{float(value):g}"
        ),
    )

    create_stability_table(
        statistics_by_case=search_time_statistics,
        output_path=(
            output_dir
            / "search_time_stability.csv"
        ),
        value_name="ms",
    )

    create_stability_table(
        statistics_by_case=memory_statistics,
        output_path=(
            output_dir
            / "memory_usage_stability.csv"
        ),
        value_name="kb",
    )

    create_report_summary_txt(
        rows=summary_rows,
        output_path=(
            output_dir
            / "report_summary.txt"
        ),
    )

    create_figure_notes(
        output_path=(
            output_dir
            / "figure_notes.txt"
        )
    )

    print("=" * 72)
    print("REPORT-READY FIGURES GENERATED SUCCESSFULLY")
    print("=" * 72)
    print(f"Summary input: {summary_path}")
    print(f"Raw input:     {raw_path}")
    print(f"Output:        {output_dir}")
    print()
    print("Created figures:")
    print("- expanded_nodes_by_level.png")
    print("- search_time_by_level.png")
    print("- memory_usage_by_level.png")
    print("- solution_quality_comparison.png")
    print()
    print("Created report data:")
    print("- expanded_nodes_table.csv")
    print("- search_time_table_ms.csv")
    print("- memory_usage_table_kb.csv")
    print("- solution_length_table.csv")
    print("- solution_cost_table.csv")
    print("- search_time_stability.csv")
    print("- memory_usage_stability.csv")
    print("- report_summary.txt")
    print("- figure_notes.txt")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())