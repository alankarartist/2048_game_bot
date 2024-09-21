from flask import Flask, Response, request
from flask_cors import CORS
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import copy

app = Flask(__name__)
CORS(app)
MOVES = [0, 1, 2, 3]  # UP, RIGHT, DOWN, LEFT
transposition_table = {}
request_counter = {}


def rotate_grid(grid, move):
    grid_2d = np.array(grid).reshape(4, 4)
    if move == 0:  # UP
        return grid_2d.flatten().tolist()
    elif move == 1:  # RIGHT
        return np.rot90(grid_2d, -1).flatten().tolist()
    elif move == 2:  # DOWN
        return np.rot90(grid_2d, 2).flatten().tolist()
    elif move == 3:  # LEFT
        return np.rot90(grid_2d, 1).flatten().tolist()


def shift_and_merge_row(row):
    new_row = [i for i in row if i != 0]  # Shift non-zero elements
    for i in range(len(new_row) - 1):
        if new_row[i] == new_row[i + 1]:
            new_row[i] *= 2
            new_row[i + 1] = 0
    new_row = [i for i in new_row if i != 0]  # Shift again after merging
    return new_row + [0] * (len(row) - len(new_row))


def apply_move(grid, move):
    grid_rotated = rotate_grid(grid, move)
    if grid_rotated is None:
        return grid
    for i in range(0, 16, 4):
        new_row = shift_and_merge_row(grid_rotated[i:i + 4])
        grid_rotated[i:i + 4] = new_row
    final_grid = rotate_grid(grid_rotated, -move)
    if final_grid is None:
        return grid_rotated
    return spawn_random_tile(final_grid)


def spawn_random_tile(grid):
    empty_cells = get_empty_cells(grid)
    if not empty_cells:
        return grid
    new_tile_value = 2 if random.random() < 0.9 else 4
    spawn_index = random.choice(empty_cells)
    grid[spawn_index] = new_tile_value
    return grid


def get_empty_cells(grid):
    return [i for i, val in enumerate(grid) if val == 0]


def score_grid(grid):
    empty_cells = len(get_empty_cells(grid))
    max_tile = max(grid)

    smoothness = 0
    grid_2d = np.array(grid).reshape(4, 4)
    for i in range(4):
        for j in range(4):
            if i < 3 and grid_2d[i, j] == grid_2d[i + 1, j]:
                smoothness += grid_2d[i, j]
            if j < 3 and grid_2d[i, j] == grid_2d[i, j + 1]:
                smoothness += grid_2d[i, j]

    monotonicity = 0
    for i in range(4):
        row = grid_2d[i]
        col = grid_2d[:, i]
        if all(x <= y for x, y in zip(row, row[1:])) or all(x >= y for x, y in zip(row, row[1:])):
            monotonicity += sum(row)
        if all(x <= y for x, y in zip(col, col[1:])) or all(x >= y for x, y in zip(col, col[1:])):
            monotonicity += sum(col)

    max_in_corner = 0
    if grid_2d[0, 0] == max_tile or grid_2d[0, 3] == max_tile or grid_2d[3, 0] == max_tile or grid_2d[3, 3] == max_tile:
        max_in_corner = max_tile

    corner_bonus = 0
    if grid_2d[0, 0] == max_tile:
        corner_bonus += max_tile
    if grid_2d[0, 3] == max_tile:
        corner_bonus += max_tile
    if grid_2d[3, 0] == max_tile:
        corner_bonus += max_tile
    if grid_2d[3, 3] == max_tile:
        corner_bonus += max_tile

    merge_potential = sum(1 for move in MOVES if apply_move(grid, move) != grid)

    return (empty_cells + 0.5 * max_tile + 0.05 * smoothness +
            0.1 * monotonicity + 0.2 * max_in_corner + corner_bonus + merge_potential)


def monte_carlo_simulation(grid, move, depth):
    grid_tuple = tuple(grid)
    if grid_tuple in transposition_table:
        return transposition_table[grid_tuple]

    sim_grid = apply_move(copy.deepcopy(grid), move)
    score = 0
    for _ in range(depth):
        if is_terminal(sim_grid):
            break
        random_move = random.choice(MOVES)
        sim_grid = apply_move(sim_grid, random_move)
        score += score_grid(sim_grid)

    transposition_table[grid_tuple] = score
    return score


def is_terminal(grid):
    if get_empty_cells(grid):
        return False
    for move in MOVES:
        if apply_move(grid, move) != grid:
            return False
    return True


def run_simulation(grid, move, simulations, depth):
    total_score = 0
    for _ in range(simulations):
        total_score += monte_carlo_simulation(grid, move, depth)
    return total_score / simulations


def get_best_move(grid):
    empty_cells = len(get_empty_cells(grid))
    simulations = 50 if empty_cells > 5 else 100  # More simulations if the grid is crowded
    depth = 30 if empty_cells > 5 else 50  # Deeper simulation as grid fills up

    move_scores = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_simulation, grid, move, simulations, depth) for move in MOVES]
        for move, future in zip(MOVES, futures):
            move_scores.append((move, future.result()))

    # Prune moves that do not change the grid
    valid_moves = [(move, score) for move, score in move_scores if apply_move(grid, move) != grid]

    # Return the best move
    if valid_moves:
        best_move = max(valid_moves, key=lambda x: x[1])[0]
        return str(best_move)
    return str(random.choice(MOVES))  # Fallback to a random move if all moves are invalid


@app.route("/")
def index():
    state = request.args.get("state")
    if not state:
        return "Missing game state!", 400
    
    if state in request_counter:
        request_counter[state] += 1
    else:
        request_counter[state] = 1
        
    grid = list(map(int, state.split(",")))

    if request_counter[state] >= 3:
        best_move = str(random.choice(MOVES))
    else:
        best_move = get_best_move(grid)

    response = Response(best_move)
    response.headers["access-control-allow-origin"] = "*"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
