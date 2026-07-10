from core.state import State
from core.game import Game


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


def calculate_path_cost(game: Game, path: list[str]) -> int | float:
    """
    Calculate the total cost of a solution path according to
    the cost function used by game.get_successors().
    """
    current_state = game.initial_state
    total_cost = 0

    for required_action in path:
        matching_successor = None

        for action, next_state, step_cost in game.get_successors(current_state):
            if action == required_action:
                matching_successor = (next_state, step_cost)
                break

        if matching_successor is None:
            raise ValueError(
                f"Invalid action {required_action!r} for the current state."
            )

        current_state, step_cost = matching_successor
        total_cost += step_cost

    return total_cost