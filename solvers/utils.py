from core.state import State


def reconstruct_path(
    parent: dict[State, tuple[State, str] | None],
    goal_state: State,
) -> list[str]:
    """
    Reconstruct the solution path from the parent dictionary.
    parent[state] = (previous_state, action)
    """
    path = []
    current_state = goal_state

    while parent[current_state] is not None:
        previous_state, action = parent[current_state]
        path.append(action)
        current_state = previous_state

    path.reverse()
    return path