import random
import pygame
import sys
import heapq
import math
from collections import deque

small_map = 5, 5
medium_map = 15, 15
large_map = 25, 25

# choose bfs, dfs, ucs, astar, astar_euclidean, greedy, minimax
ALGORITHM = "expectimax"

MAP_SIZE = large_map if ALGORITHM == "minimax" else medium_map

EVADE_WEIGHT = 80.0  # sorcerer-pursuit / player-flee strength (inverse proximity)
W_GOAL = 1.5  # player values collecting gems / reaching the exit
MINIMAX_DEPTH = 4  # lookahead plies (one player move + one sorcerer reply per pair)
CAPTURE_REWARD = 1000  # |value| for catch/win — dominates heuristic
GEM_COST = 12.0  # reward per uncollected gem; > typical nearest-gem delta so collecting pays off
REVISIT_PENALTY = 50.0  # discourages re-entering recently-occupied cells to break oscillation
HAZARD_PENALTY_M = 8.0  # 'M' tile penalty; scaled below GEM_COST so a short detour usually pays off
HAZARD_PENALTY_S = 32.0  # 'S' tile penalty, ~4x HAZARD_PENALTY_M to mirror TILE_COSTS' M=5/S=20 ratio


def get_sprite(sheet, x, y, width, height, scale_to):
    sprite = pygame.Surface((width, height), pygame.SRCALPHA)
    sprite.blit(sheet, (0, 0), (x, y, width, height))
    return pygame.transform.scale(sprite, (scale_to, scale_to))


def construct_map(rows, cols):
    arr = [['.' for _ in range(cols)] for _ in range(rows)]
    valid_exit_borders = []

    for r in range(rows):
        for c in range(cols):
            if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                arr[r][c] = '#'

                is_corner = (r == 0 and c == 0) or \
                            (r == 0 and c == cols - 1) or \
                            (r == rows - 1 and c == 0) or \
                            (r == rows - 1 and c == cols - 1)

                if not is_corner:
                    valid_exit_borders.append((r, c))

    if valid_exit_borders:
        exit_r, exit_c = random.choice(valid_exit_borders)
        arr[exit_r][exit_c] = 'E'

    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if arr[r][c] == '.' and (r, c) != (1, 1):
                hazard_chance = random.random()
                if hazard_chance < 0.15:
                    arr[r][c] = 'M'
                elif hazard_chance < 0.20:
                    arr[r][c] = 'S'

    arr[1][1] = 'G'
    arr[1][cols - 2] = 'G'
    arr[rows - 2][1] = 'G'
    arr[rows - 2][cols - 2] = 'G'

    center_r, center_c = rows // 2, cols // 2

    arr[center_r][center_c] = 'P'

    return arr


def get_valid_moves(r, c, grid, rows, cols):
    """Used by minimax mode: unlike the pathfinders below, this has no notion
    of 'visited' -- it's a per-turn legal-move query, not a search primitive."""
    valid_moves = []
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    for dr, dc in directions:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != '#':
            valid_moves.append((nr, nc))
    return valid_moves


def find_player(grid, rows, cols):
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 'P':
                return r, c
    return None, None


def find_exit(grid, rows, cols):
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 'E':
                return r, c
    return None, None


def find_gems(grid, rows, cols):
    gems = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 'G':
                gems.append((r, c))
    return tuple(gems)


def manhattan_distance(r1, c1, r2, c2):
    return abs(r1 - r2) + abs(c1 - c2)


def euclidean_distance(r1, c1, r2, c2):
    return math.sqrt((r1 - r2) ** 2 + (c1 - c2) ** 2)


def multi_target_heuristic(r, c, uncollected_gems, exit_r, exit_c, distance_func=manhattan_distance):
    # find the (distance_func) distance to the closest gem
    if len(uncollected_gems) > 0:
        distances = [abs(r - gr) + abs(c - gc) for gr, gc in uncollected_gems]
        return min(distances)
    else:
        return distance_func(r, c, exit_r, exit_c)


def bfs(grid, rows, cols):
    start_r, start_c = find_player(grid, rows, cols)
    queue = [(start_r, start_c, [])]
    visited = {(start_r, start_c)}

    directions = {
        (-1, 0): "UP",
        (1, 0): "DOWN",
        (0, -1): "LEFT",
        (0, 1): "RIGHT"
    }

    while queue:
        r, c, path = queue.pop(0)

        if grid[r][c] == 'E':
            print(f"Path found in: {len(path)} steps")
            return path

        for dr, dc in directions.keys():
            nr, nc = r + dr, c + dc
            if (0 <= nr < rows) and (0 <= nc < cols):
                if grid[nr][nc] != '#' and (nr, nc) not in visited:
                    visited.add((nr, nc))

                    move_name = directions[(dr, dc)]
                    new_path = path + [move_name]

                    queue.append((nr, nc, new_path))

    print("No path found")
    return None


def dfs(grid, rows, cols):
    start_r, start_c = find_player(grid, rows, cols)
    # uses a stack (LIFO) for DFS instead of a queue (FIFO) for BFS
    stack = [(start_r, start_c, [])]
    # keeps track of nodes that are fully processed
    visited = set()

    directions = {
        (-1, 0): "UP",
        (1, 0): "DOWN",
        (0, -1): "LEFT",
        (0, 1): "RIGHT"
    }

    while stack:
        # pop from the end of a list to simulate a stack (LIFO)
        r, c, path = stack.pop()

        if grid[r][c] == 'E':
            print(f"Path found in: {len(path)} steps")
            return path

        # for DFS, mark node as visited when it is popped and processed
        if (r, c) not in visited:
            visited.add((r, c))

            for dr, dc in directions.keys():
                nr, nc = r + dr, c + dc
                if (0 <= nr < rows) and (0 <= nc < cols):
                    if grid[nr][nc] != '#' and (nr, nc) not in visited:
                        move_name = directions[(dr, dc)]
                        new_path = path + [move_name]
                        stack.append((nr, nc, new_path))

    print("No path found")
    return None


def ucs(grid, rows, cols):
    start_r, start_c = find_player(grid, rows, cols)
    pq = [(0, start_r, start_c, [])]  # priority queue that stores total_cost, current row/col, path so far
    visited = set()

    directions = {
        (-1, 0): "UP",
        (1, 0): "DOWN",
        (0, -1): "LEFT",
        (0, 1): "RIGHT"
    }

    TILE_COSTS = {
        '.': 1,
        'E': 1,
        'P': 1,
        'M': 5,
        'S': 20
    }

    while pq:
        cost, r, c, path = heapq.heappop(pq)  # always grabs the tuple with the lowest cost

        # check visited after popping
        if (r, c) in visited:
            continue
        visited.add((r, c))

        # if exit is reached print how many steps and costs
        if grid[r][c] == 'E':
            print(f"Path found in: {len(path)} steps, cost: {cost}")
            return path

        # scan neighbours
        for dr, dc in directions.keys():
            nr, nc = r + dr, c + dc

            if (0 <= nr < rows) and (0 <= nc < cols):
                tile_type = grid[nr][nc]

                if tile_type != '#' and (nr, nc) not in visited:
                    step_cost = TILE_COSTS.get(tile_type, 1)  # default cost is 1 if tile type is not in TILE_COSTS
                    new_cost = cost + step_cost

                    move_name = directions[(dr, dc)]
                    new_path = path + [move_name]

                    heapq.heappush(pq, (new_cost, nr, nc, new_path))

    print("No path found")
    return None


def a_star(grid, rows, cols, distance_func=manhattan_distance):
    start_r, start_c = find_player(grid, rows, cols)
    exit_r, exit_c = find_exit(grid, rows, cols)

    initial_gems = find_gems(grid, rows, cols)

    if exit_r is None:
        print("Error: no exit found on map")
        return None

    # calculates the inital heuristic
    start_h = multi_target_heuristic(start_r, start_c, initial_gems, exit_r, exit_c, distance_func)

    pq = [(start_h, 0, start_r, start_c, initial_gems,
           [])]  # priority queue that stores total_cost, current row/col, path so far
    visited = set()

    directions = {
        (-1, 0): "UP",
        (1, 0): "DOWN",
        (0, -1): "LEFT",
        (0, 1): "RIGHT"
    }

    TILE_COSTS = {
        '.': 1,
        'E': 1,
        'G': 1,
        'P': 1,
        'M': 5,
        'S': 20
    }

    while pq:
        f, g, r, c, gems_left, path = heapq.heappop(pq)  # always grabs the tuple with the lowest cost

        state = (r, c, gems_left)
        # check visited after popping
        if state in visited:
            continue
        visited.add(state)

        # if exit is reached print how many steps and costs
        if grid[r][c] == 'E' and len(gems_left) == 0:
            print(f"A* path found in: {len(path)} steps, cost: {f}")
            return path

        # scan neighbours
        for dr, dc in directions.keys():
            nr, nc = r + dr, c + dc

            if (0 <= nr < rows) and (0 <= nc < cols):
                tile_type = grid[nr][nc]

                if tile_type != '#':
                    new_gems = gems_left
                    if (nr, nc) in gems_left:
                        new_gems = tuple(gem for gem in gems_left if gem != (nr, nc))

                    new_state = (nr, nc, new_gems)
                    if new_state not in visited:
                        step_cost = TILE_COSTS.get(tile_type, 1)  # default cost is 1 if tile type is not in TILE_COSTS
                        new_g = g + step_cost

                        new_h = multi_target_heuristic(nr, nc, new_gems, exit_r, exit_c, distance_func)
                        new_f = new_g + new_h

                        move_name = directions[(dr, dc)]
                        new_path = path + [move_name]

                        heapq.heappush(pq, (new_f, new_g, nr, nc, new_gems, new_path))

    print("No path found")
    return None


def greedy_search(grid, rows, cols):
    start_r, start_c = find_player(grid, rows, cols)
    exit_r, exit_c = find_exit(grid, rows, cols)

    if exit_r is None:
        print("Error: no exit found on map")
        return None

    # calculates the inital heuristic
    start_h = manhattan_distance(start_r, start_c, exit_r, exit_c)

    pq = [(start_h, 0, start_r, start_c, [])]  # priority queue that stores total_cost, current row/col, path so far
    visited = set()

    directions = {
        (-1, 0): "UP",
        (1, 0): "DOWN",
        (0, -1): "LEFT",
        (0, 1): "RIGHT"
    }

    TILE_COSTS = {
        '.': 1,
        'E': 1,
        'P': 1,
        'M': 5,
        'S': 20
    }

    while pq:
        f, g, r, c, path = heapq.heappop(pq)  # always grabs the tuple with the lowest cost

        # check visited after popping
        if (r, c) in visited:
            continue
        visited.add((r, c))

        # if exit is reached print how many steps and costs
        if grid[r][c] == 'E':
            print(f"Greedy path found in: {len(path)} steps, cost: {f}")
            return path

        # scan neighbours
        for dr, dc in directions.keys():
            nr, nc = r + dr, c + dc

            if (0 <= nr < rows) and (0 <= nc < cols):
                tile_type = grid[nr][nc]

                if tile_type != '#' and (nr, nc) not in visited:
                    step_cost = TILE_COSTS.get(tile_type, 1)  # default cost is 1 if tile type is not in TILE_COSTS
                    new_g = g + step_cost

                    new_h = manhattan_distance(nr, nc, exit_r, exit_c)

                    new_f = new_h

                    move_name = directions[(dr, dc)]
                    new_path = path + [move_name]

                    heapq.heappush(pq, (new_f, new_g, nr, nc, new_path))

    print("No path found")
    return None


PATHFINDERS = {
    "bfs": lambda grid, rows, cols: bfs(grid, rows, cols),
    "dfs": lambda grid, rows, cols: dfs(grid, rows, cols),
    "ucs": lambda grid, rows, cols: ucs(grid, rows, cols),
    "astar": lambda grid, rows, cols: a_star(grid, rows, cols, distance_func=manhattan_distance),
    "astar_euclidean": lambda grid, rows, cols: a_star(grid, rows, cols, distance_func=euclidean_distance),
    "greedy": lambda grid, rows, cols: greedy_search(grid, rows, cols),
}


def evaluate(grid, sorcerer_r, sorcerer_c, player_r, player_c, gems_left, exit_r, exit_c):
    if (sorcerer_r, sorcerer_c) == (player_r, player_c):
        return CAPTURE_REWARD  # catch = best for sorcerer (max)
    if grid[player_r][player_c] == 'E' and len(gems_left) == 0:
        return -CAPTURE_REWARD  # player wins = worst for the sorcerer (min)
    dist = manhattan_distance(sorcerer_r, sorcerer_c, player_r, player_c)

    evade = EVADE_WEIGHT / (dist + 1)

    goal = W_GOAL * (len(gems_left) * GEM_COST
                     + multi_target_heuristic(player_r, player_c, gems_left, exit_r, exit_c))
    return evade + goal


def minimax(grid, depth, is_maximizing, sorcerer_r, sorcerer_c, player_r, player_c, rows, cols, gems_left, exit_r,
            exit_c, alpha=float("-inf"), beta=float("inf")):
    if (sorcerer_r, sorcerer_c) == (player_r, player_c): return CAPTURE_REWARD
    if grid[player_r][player_c] == 'E' and len(gems_left) == 0: return -CAPTURE_REWARD
    if depth == 0: return evaluate(grid, sorcerer_r, sorcerer_c, player_r, player_c, gems_left, exit_r, exit_c)

    if is_maximizing:
        # sorcerers turn - collects no gems, gems-left passes through unchanged
        max_eval = float("-inf")
        moves = get_valid_moves(sorcerer_r, sorcerer_c, grid, rows, cols)
        for nr, nc in moves:
            ev = minimax(grid, depth - 1, False, nr, nc, player_r, player_c, rows, cols, gems_left, exit_r, exit_c,
                         alpha, beta)
            max_eval = max(max_eval, ev)
            alpha = max(alpha, ev)
            if alpha >= beta:
                break
        if not moves:  # cornered sorcerer - stay put, let player move
            return minimax(grid, depth - 1, False, sorcerer_r, sorcerer_c, player_r, player_c,
                           rows, cols, gems_left, exit_r, exit_c, alpha, beta)
        return max_eval

    else:
        # player's turn — collect any gem landed on, then let the sorcerer reply
        min_eval = float("inf")
        moves = get_valid_moves(player_r, player_c, grid, rows, cols)
        for nr, nc in moves:
            new_gems = tuple(g for g in gems_left if g != (nr, nc)) if (nr, nc) in gems_left else gems_left
            ev = minimax(grid, depth - 1, True, sorcerer_r, sorcerer_c, nr, nc,
                         rows, cols, new_gems, exit_r, exit_c, alpha, beta)
            # discourage (but don't forbid) routing the player through hazard tiles;
            # applied at every ply of the lookahead so a path crossing multiple
            # hazards is penalised more than one crossing a single hazard
            landing_tile = grid[nr][nc]
            if landing_tile == 'M':
                ev += HAZARD_PENALTY_M
            elif landing_tile == 'S':
                ev += HAZARD_PENALTY_S
            min_eval = min(min_eval, ev)
            beta = min(beta, ev)
            if beta <= alpha:
                break
        if not moves:
            return minimax(grid, depth - 1, True, sorcerer_r, sorcerer_c, player_r, player_c,
                           rows, cols, gems_left, exit_r, exit_c, alpha, beta)
        return min_eval


def expectimax(grid, depth, is_chance, sorcerer_r, sorcerer_c, player_r, player_c, rows, cols, gems_left, exit_r,
               exit_c):
    if (sorcerer_r, sorcerer_c) == (player_r, player_c): return CAPTURE_REWARD
    if grid[player_r][player_c] == 'E' and len(gems_left) == 0: return -CAPTURE_REWARD
    if depth == 0: return evaluate(grid, sorcerer_r, sorcerer_c, player_r, player_c, gems_left, exit_r, exit_c)

    if is_chance:
        moves = get_valid_moves(sorcerer_r, sorcerer_c, grid, rows, cols)
        if not moves:  # cornered sorcerer - stay put, let player move
            return expectimax(grid, depth - 1, False, sorcerer_r, sorcerer_c, player_r, player_c, rows, cols, gems_left,
                              exit_r, exit_c)
        total = 0.0
        for nr, nc in moves:
            total += expectimax(grid, depth - 1, False, nr, nc, player_r, player_c, rows, cols, gems_left,
                                exit_r, exit_c)
        return total / len(moves)  # uniform average for sorcerers moves

    else:
        min_eval = float("inf")
        moves = get_valid_moves(player_r, player_c, grid, rows, cols)
        for nr, nc in moves:
            new_gems = tuple(g for g in gems_left if g != (nr, nc)) if (nr, nc) in gems_left else gems_left
            ev = expectimax(grid, depth - 1, True, sorcerer_r, sorcerer_c, nr, nc,
                            rows, cols, new_gems, exit_r, exit_c)
            # same hazard shaping as minimax(), applied at every ply of the lookahead
            landing_tile = grid[nr][nc]
            if landing_tile == 'M':
                ev += HAZARD_PENALTY_M
            elif landing_tile == 'S':
                ev += HAZARD_PENALTY_S
            min_eval = min(min_eval, ev)
        if not moves:
            return expectimax(grid, depth - 1, True, sorcerer_r, sorcerer_c, player_r, player_c,
                              rows, cols, gems_left, exit_r, exit_c)
        return min_eval


def get_best_sorcerer_move(grid, sorcerer_r, sorcerer_c, player_r, player_c,
                           gems_left, exit_r, exit_c, rows, cols, depth=2, avoid=None):
    best_moves = [(sorcerer_r, sorcerer_c)]
    max_eval = float("-inf")
    alpha = float("-inf")
    beta = float("inf")
    cur_dist = manhattan_distance(sorcerer_r, sorcerer_c, player_r, player_c)
    for nr, nc in get_valid_moves(sorcerer_r, sorcerer_c, grid, rows, cols):
        ev = minimax(grid, depth - 1, False, nr, nc, player_r, player_c,
                     rows, cols, gems_left, exit_r, exit_c, alpha, beta)
        # penalise re-entering a recently-occupied cell to break pursuit/evasion
        # oscillation -- but only when the move ISN'T already closing distance
        # on the player, so genuine forward pursuit is never blocked by history
        making_progress = manhattan_distance(nr, nc, player_r, player_c) < cur_dist
        if avoid is not None and (nr, nc) in avoid and not making_progress:
            ev -= REVISIT_PENALTY
        if ev > max_eval:
            max_eval = ev
            best_moves = [(nr, nc)]
        elif ev == max_eval:
            # tie for best score -> keep all equally-good candidates, don't let
            # the fixed [RIGHT, LEFT, DOWN, UP] iteration order silently pick a winner
            best_moves.append((nr, nc))

        alpha = max(alpha, max_eval)
    return random.choice(best_moves)


def get_best_player_move(grid, sorcerer_r, sorcerer_c, player_r, player_c,
                         gems_left, exit_r, exit_c, rows, cols, depth=2, avoid=None):
    best_moves = [(player_r, player_c)]
    min_eval = float("inf")
    alpha = float("-inf")
    beta = float("inf")
    cur_dist = multi_target_heuristic(player_r, player_c, gems_left, exit_r, exit_c)
    for nr, nc in get_valid_moves(player_r, player_c, grid, rows, cols):
        new_gems = tuple(g for g in gems_left if g != (nr, nc)) if (nr, nc) in gems_left else gems_left
        ev = minimax(grid, depth - 1, True, sorcerer_r, sorcerer_c, nr, nc,
                     rows, cols, new_gems, exit_r, exit_c, alpha, beta)
        # discourage stepping onto a hazard tile this turn, same weighting as
        # the in-recursion penalty in minimax() so the immediate move and the
        # lookahead agree with each other
        landing_tile = grid[nr][nc]
        if landing_tile == 'M':
            ev += HAZARD_PENALTY_M
        elif landing_tile == 'S':
            ev += HAZARD_PENALTY_S
        # penalise re-entering a recently-occupied cell to break pursuit/evasion
        # oscillation -- but only when the move ISN'T already collecting a gem
        # or reducing distance to the nearest remaining gem/exit
        new_dist = multi_target_heuristic(nr, nc, new_gems, exit_r, exit_c)
        making_progress = (nr, nc) in gems_left or new_dist < cur_dist
        if avoid is not None and (nr, nc) in avoid and not making_progress:
            ev += REVISIT_PENALTY
        if ev < min_eval:
            min_eval = ev
            best_moves = [(nr, nc)]
        elif ev == min_eval:
            best_moves.append((nr, nc))

        beta = min(beta, min_eval)
    return random.choice(best_moves)


# player-side move selection in expectimax mode - alpha and beta isn't parsed and instead of calling minimax(), expectimax is called
def get_best_player_move_expectimax(grid, sorcerer_r, sorcerer_c, player_r, player_c, gems_left, exit_r, exit_c, rows,
                                    cols, depth=2, avoid=None):
    best_moves = [(player_r, player_c)]
    min_eval = float("inf")
    cur_dist = multi_target_heuristic(player_r, player_c, gems_left, exit_r, exit_c)
    for nr, nc in get_valid_moves(player_r, player_c, grid, rows, cols):
        new_gems = tuple(g for g in gems_left if g != (nr, nc)) if (nr, nc) in gems_left else gems_left
        ev = expectimax(grid, depth - 1, True, sorcerer_r, sorcerer_c, nr, nc,
                        rows, cols, new_gems, exit_r, exit_c)
        landing_tile = grid[nr][nc]
        if landing_tile == 'M':
            ev += HAZARD_PENALTY_M
        elif landing_tile == 'S':
            ev += HAZARD_PENALTY_S
        new_dist = multi_target_heuristic(nr, nc, new_gems, exit_r, exit_c)
        making_progress = (nr, nc) in gems_left or new_dist < cur_dist
        if avoid is not None and (nr, nc) in avoid and not making_progress:
            ev += REVISIT_PENALTY
        if ev < min_eval:
            min_eval = ev
            best_moves = [(nr, nc)]
        elif ev == min_eval:
            best_moves.append((nr, nc))

    return random.choice(best_moves)


# sorcerers behaviour in expectimax mode: chooses randomly among legal moves.
def get_random_sorcerer_move(grid, sorcerer_r, sorcerer_c, rows, cols):
    moves = get_valid_moves(sorcerer_r, sorcerer_c, grid, rows, cols)
    if not moves:
        return sorcerer_r, sorcerer_c
    return random.choice(moves)


def render_map(screen, my_map, rows, cols, SPRITES, TILE_SIZE, player_pos, sorcerer_pos=None):
    for r in range(rows):
        for c in range(cols):
            rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            screen.blit(SPRITES['.'], rect)

            tile_type = my_map[r][c]
            if tile_type != '.':
                if tile_type == '#':
                    if r == 0 and c == 0:
                        sprite_to_draw = SPRITES['WALL_TL']
                    elif r == 0 and c == cols - 1:
                        sprite_to_draw = SPRITES['WALL_TR']
                    elif r == rows - 1 and c == 0:
                        sprite_to_draw = SPRITES['WALL_BL']
                    elif r == rows - 1 and c == cols - 1:
                        sprite_to_draw = SPRITES['WALL_BR']
                    elif r == 0:
                        sprite_to_draw = SPRITES['WALL_T']
                    elif r == rows - 1:
                        sprite_to_draw = SPRITES['WALL_B']
                    elif c == 0:
                        sprite_to_draw = SPRITES['WALL_L']
                    elif c == cols - 1:
                        sprite_to_draw = SPRITES['WALL_R']
                    else:
                        sprite_to_draw = SPRITES['#']
                else:
                    sprite_to_draw = SPRITES.get(tile_type, SPRITES['.'])

                screen.blit(sprite_to_draw, rect)

            if (r, c) == player_pos:
                screen.blit(SPRITES['P'], rect)
            elif sorcerer_pos is not None and (r, c) == sorcerer_pos:
                screen.blit(SPRITES['X'], rect)


def run_pathfinding_mode(screen, clock, my_map, rows, cols, SPRITES, TILE_SIZE, algorithm):
    path_fn = PATHFINDERS[algorithm]
    path = path_fn(my_map, rows, cols)

    player_r, player_c = find_player(my_map, rows, cols)
    my_map[player_r][player_c] = '.'  # erase the player from the static map array

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # If we have a path, and there are still moves left in it
        if path and len(path) > 0:
            move = path.pop(0)  # Take the very first move off the list

            target_r, target_c = player_r, player_c

            if move == "UP":
                target_r -= 1
            elif move == "DOWN":
                target_r += 1
            elif move == "LEFT":
                target_c -= 1
            elif move == "RIGHT":
                target_c += 1

            # Execute the move in the array
            if my_map[target_r][target_c] != '#':
                player_r, player_c = target_r, target_c

                if my_map[target_r][target_c] == 'G':
                    my_map[target_r][target_c] = '.'

                if my_map[player_r][player_c] == 'E' and len(path) == 0:
                    print("Success! you reached the stairs.")

        screen.fill((0, 0, 0))
        render_map(screen, my_map, rows, cols, SPRITES, TILE_SIZE, (player_r, player_c))
        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
    sys.exit()


def run_minimax_mode(screen, clock, my_map, rows, cols, SPRITES, TILE_SIZE):
    player_r, player_c = find_player(my_map, rows, cols)
    my_map[player_r][player_c] = '.'  # erase the player from the static map array

    sorcerer_r, sorcerer_c = rows - 2, cols - 3

    exit_r, exit_c = find_exit(my_map, rows, cols)

    game_over = False

    player_history = deque(maxlen=8)  # recent player cells, used to discourage oscillation
    sorcerer_history = deque(maxlen=8)  # recent sorcerer cells

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if not game_over:
            gems_left = find_gems(my_map, rows, cols)

            player_history.append((player_r, player_c))
            player_r, player_c = get_best_player_move(
                my_map, sorcerer_r, sorcerer_c, player_r, player_c,
                gems_left, exit_r, exit_c, rows, cols, MINIMAX_DEPTH,
                avoid=set(player_history)
            )

            if my_map[player_r][player_c] == 'G':
                my_map[player_r][player_c] = '.'

            remaining_gems = find_gems(my_map, rows, cols)
            if my_map[player_r][player_c] == 'E' and len(remaining_gems) == 0:
                print("Success! you reached the stairs.")
                game_over = True

            if not game_over:
                if (sorcerer_r, sorcerer_c) != (player_r, player_c):
                    sorcerer_history.append((sorcerer_r, sorcerer_c))
                    sorcerer_r, sorcerer_c = get_best_sorcerer_move(
                        my_map, sorcerer_r, sorcerer_c, player_r, player_c,
                        remaining_gems, exit_r, exit_c, rows, cols, MINIMAX_DEPTH,
                        avoid=set(sorcerer_history)
                    )

                if (sorcerer_r, sorcerer_c) == (player_r, player_c):
                    print("DEATH! The sorcerer caught you.")
                    game_over = True

        screen.fill((0, 0, 0))
        render_map(screen, my_map, rows, cols, SPRITES, TILE_SIZE, (player_r, player_c), (sorcerer_r, sorcerer_c))
        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
    sys.exit()


def run_expectimax_mode(screen, clock, my_map, rows, cols, SPRITES, TILE_SIZE):
    player_r, player_c = find_player(my_map, rows, cols)
    my_map[player_r][player_c] = '.'  # erase the player from the map array

    sorcerer_r, sorcerer_c = rows - 2, cols - 3

    exit_r, exit_c = find_exit(my_map, rows, cols)

    game_over = False

    player_history = deque(maxlen=8)  # recent player cells, used to discourage oscillation

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if not game_over:
            gems_left = find_gems(my_map, rows, cols)

            player_history.append((player_r, player_c))
            player_r, player_c = get_best_player_move_expectimax(
                my_map, sorcerer_r, sorcerer_c, player_r, player_c,
                gems_left, exit_r, exit_c, rows, cols, MINIMAX_DEPTH,
                avoid=set(player_history)
            )

            if my_map[player_r][player_c] == 'G':
                my_map[player_r][player_c] = '.'

            remaining_gems = find_gems(my_map, rows, cols)
            if my_map[player_r][player_c] == 'E' and len(remaining_gems) == 0:
                print("Success! you reached the stairs.")
                game_over = True

            if not game_over:
                if (sorcerer_r, sorcerer_c) != (player_r, player_c):
                    # chance-node assumption in get_best_player_move_expectimax
                    sorcerer_r, sorcerer_c = get_random_sorcerer_move(
                        my_map, sorcerer_r, sorcerer_c, rows, cols
                    )

                if (sorcerer_r, sorcerer_c) == (player_r, player_c):
                    print("DEATH! The sorcerer caught you.")
                    game_over = True

        screen.fill((0, 0, 0))
        render_map(screen, my_map, rows, cols, SPRITES, TILE_SIZE, (player_r, player_c), (sorcerer_r, sorcerer_c))
        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
    sys.exit()


def main():
    pygame.init()

    # Settings
    TILE_SIZE = 32  # Scaled up from 16 for better visibility
    NATIVE_TILE = 16  # The actual pixel size of the tiles

    rows, cols = MAP_SIZE
    my_map = construct_map(rows, cols)

    # Set up the display
    screen_width = cols * TILE_SIZE
    screen_height = rows * TILE_SIZE
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption(f'Dungeon Crawler - {ALGORITHM.upper()} Agent')

    # loads spritesheet and handles error if not found
    try:
        Dungeon_sprite_sheet = pygame.image.load("assets/Dungeon_Tileset.png").convert_alpha()
        Character_sprite_sheet = pygame.image.load("assets/Dungeon_Character.png").convert_alpha()
    except FileNotFoundError:
        print("Error: Couldn't find 'Dungeon_Tileset.png' or 'Character_Tileset.png'")
        pygame.quit()
        sys.exit()

    SPRITES = {
        '.': get_sprite(Dungeon_sprite_sheet, 112, 0, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        '#': get_sprite(Dungeon_sprite_sheet, 16, 0, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'E': get_sprite(Dungeon_sprite_sheet, 144, 48, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'M': get_sprite(Dungeon_sprite_sheet, 128, 96, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'S': get_sprite(Dungeon_sprite_sheet, 112, 112, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'G': get_sprite(Dungeon_sprite_sheet, 96, 128, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'P': get_sprite(Character_sprite_sheet, 64, 32, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'X': get_sprite(Character_sprite_sheet, 64, 48, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),

        'WALL_T': get_sprite(Dungeon_sprite_sheet, 16, 0, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'WALL_B': get_sprite(Dungeon_sprite_sheet, 16, 64, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'WALL_L': get_sprite(Dungeon_sprite_sheet, 0, 16, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'WALL_R': get_sprite(Dungeon_sprite_sheet, 80, 16, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'WALL_TL': get_sprite(Dungeon_sprite_sheet, 0, 0, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'WALL_TR': get_sprite(Dungeon_sprite_sheet, 80, 0, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'WALL_BL': get_sprite(Dungeon_sprite_sheet, 0, 64, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'WALL_BR': get_sprite(Dungeon_sprite_sheet, 80, 64, NATIVE_TILE, NATIVE_TILE, TILE_SIZE)
    }

    clock = pygame.time.Clock()

    if ALGORITHM == "minimax":
        run_minimax_mode(screen, clock, my_map, rows, cols, SPRITES, TILE_SIZE)
    elif ALGORITHM == "expectimax":
        run_expectimax_mode(screen, clock, my_map, rows, cols, SPRITES, TILE_SIZE)
    elif ALGORITHM in PATHFINDERS:
        run_pathfinding_mode(screen, clock, my_map, rows, cols, SPRITES, TILE_SIZE, ALGORITHM)
    else:
        valid = ", ".join(list(PATHFINDERS.keys()) + ["minimax"])
        print(f"Unknown ALGORITHM '{ALGORITHM}'. Valid options: {valid}")
        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    main()
