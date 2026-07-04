class Board:
    def __init__(self, name, grid, start, goal, bridges=None, switches=None):
        self.name = name # Name of the level
        self.grid = grid
        self.start = start
        self.goal = goal
        self.rows = len(grid)
        self.cols = len(grid[0])

        # List of bridge definitions loaded from JSON.
        # Example:
        # [
        #     {
        #         "id": 0,
        #         "positions": [[0, 2]],
        #         "initial_open": false
        #     }
        # ]
        self.bridges = bridges or []

        # Map each bridge cell position to its bridge id.
        # Example:
        # (0, 2) -> 0
        self.bridge_positions = {}

        # Store the initial open/closed status of every bridge.
        # False = closed, True = open.
        initial_bridge_states = [False] * len(self.bridges)

        for bridge in self.bridges:
            bridge_id = bridge["id"]

            if bridge_id < 0 or bridge_id >= len(self.bridges):
                raise ValueError(f"Invalid bridge id: {bridge_id}")

            initial_bridge_states[bridge_id] = bridge.get("initial_open", False)

            for row, col in bridge["positions"]:
                self.bridge_positions[(row, col)] = bridge_id

        # This tuple will be copied into the initial State.
        self.initial_bridges = tuple(initial_bridge_states)

        # SWITCHES
        # List of switch definitions loaded from JSON.
        self.switches = switches or []

        # Map each switch cell position to its switch data.
        # Example:
        # (1, 2) -> {
        #     "position": [1, 2],
        #     "type": "soft",
        #     "bridge_ids": [0],
        #     "behavior": "toggle"
        # }
        self.switch_positions = {}

        for switch in self.switches:
            row, col = switch["position"]
            self.switch_positions[(row, col)] = switch

            # Validate linked bridge ids.
            for bridge_id in switch.get("bridge_ids", []):
                if bridge_id < 0 or bridge_id >= len(self.bridges):
                    raise ValueError(
                        f"Switch at ({row}, {col}) refers to invalid bridge id: {bridge_id}"
                    )


    def in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols


    def get_tile(self, row, col):
        if not self.in_bounds(row, col):
            return None
        return self.grid[row][col]
    

    def get_bridge_id(self, row, col):
        # Return None if this position is not a bridge cell.
        return self.bridge_positions.get((row, col))
    
    
    def get_switch(self, row, col):
        # Return None if this position is not a switch cell.
        return self.switch_positions.get((row, col))