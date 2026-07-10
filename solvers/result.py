from dataclasses import dataclass


@dataclass
class SearchResult:
    """
    Store the result and performance information of a search algorithm.
    """
    path: list[str] | None
    search_time: float
    memory_usage: int
    expanded_nodes: int
    solution_length: int | None

    # Total path cost according to the non-uniform cost function.
    solution_cost: int | float | None = None