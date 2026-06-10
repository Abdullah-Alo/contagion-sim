import numpy as np
import json

S = 0  # Susceptible
I = 1  # Infected
R = 2  # Recovered
P = 3  # Patched

class MalwareGrid:
    def __init__(self, rows=80, cols=80, infect_rate=0.3, recover_rate=0.05,
                 patch_rate=0.0, topology="Grid", reinfection=False):
        self.rows = rows
        self.cols = cols
        self.infect_rate = infect_rate
        self.recover_rate = recover_rate
        self.patch_rate = patch_rate
        self.topology = topology
        self.reinfection = reinfection
        self.grid = np.zeros((rows, cols), dtype=int)
        self.tick = 0

    @classmethod
    def from_profile(cls, path, rows=80, cols=80):
        with open(path, "r") as f:
            p = json.load(f)
        instance = cls(
            rows=rows,
            cols=cols,
            infect_rate=p["infect_rate"],
            recover_rate=p["recover_rate"],
            patch_rate=p["patch_rate"],
            topology=p["topology"],
            reinfection=p.get("reinfection", False),
        )
        instance.profile = p
        return instance

    def seed_patient_zero(self, row=None, col=None):
        r = row if row is not None else self.rows // 2
        c = col if col is not None else self.cols // 2
        self.grid[r, c] = I

    def step(self):
        new_grid = self.grid.copy()
        for r in range(self.rows):
            for c in range(self.cols):
                state = self.grid[r, c]
                if state == S:
                    neighbors = self._get_neighbors(r, c)
                    infected_neighbors = sum(1 for n in neighbors if self.grid[n] == I)
                    if infected_neighbors > 0 and np.random.random() < self.infect_rate:
                        new_grid[r, c] = I
                    elif np.random.random() < self.patch_rate:
                        new_grid[r, c] = P
                elif state == I:
                    if np.random.random() < self.recover_rate:
                        new_grid[r, c] = R
                elif state == R and self.reinfection:
                    neighbors = self._get_neighbors(r, c)
                    infected_neighbors = sum(1 for n in neighbors if self.grid[n] == I)
                    if infected_neighbors > 0 and np.random.random() < self.infect_rate * 0.3:
                        new_grid[r, c] = I
        self.grid = new_grid
        self.tick += 1

    def _get_neighbors(self, r, c):
        topo = self.topology[0] if isinstance(self.topology, tuple) else self.topology

        if topo == "Grid":
            neighbors = []
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    neighbors.append((nr, nc))
            return neighbors

        elif topo == "Random":
            indices = np.random.randint(0, self.rows * self.cols, 8)
            return [(idx // self.cols, idx % self.cols) for idx in indices]

        elif topo == "Hub-and-spoke":
            is_hub = (r * self.cols + c) % 10 == 0
            k = 20 if is_hub else 2
            indices = np.random.randint(0, self.rows * self.cols, k)
            return [(idx // self.cols, idx % self.cols) for idx in indices]

        else:
            neighbors = []
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    neighbors.append((nr, nc))
            return neighbors

    def counts(self):
        return {
            'S': int(np.sum(self.grid == S)),
            'I': int(np.sum(self.grid == I)),
            'R': int(np.sum(self.grid == R)),
            'P': int(np.sum(self.grid == P)),
        }