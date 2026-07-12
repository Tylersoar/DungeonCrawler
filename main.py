import random
import pygame
import sys
import heapq

small_map = 5, 5
medium_map = 15, 15
large_map = 30, 30
CAPTURE_REWARD = 1000
EVADE_WEIGHT = 80.0
W_GOAL = 1.5
GEM_COST = 12.0

HAZARD_PENALTY_M = 8.0
HAZARD_PENALTY_S = 32.0
REVISIT_PENALTY = 50.0


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


def multi_target_heuristic(r, c, uncollected_gems, exit_r, exit_c):
    # find the Manhattan distance to the closest gem
    if len(uncollected_gems) > 0:
        distances = [abs(r - gr) + abs(c - gc) for gr, gc in uncollected_gems]
        return min(distances)
    else:
        return abs(r - exit_r) + abs(c - exit_c)


def manhattan_distance(r1, c1, r2, c2):
    return abs(r1 - r2) + abs(c1 - c2)


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


def a_star(grid, rows, cols):
    start_r, start_c = find_player(grid, rows, cols)
    exit_r, exit_c = find_exit(grid, rows, cols)

    initial_gems = find_gems(grid, rows, cols)

    if exit_r is None:
        print("Error: no exit found on map")
        return None

    # calculates the inital heuristic
    start_h = multi_target_heuristic(start_r, start_c, initial_gems, exit_r, exit_c)

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

                        new_h = multi_target_heuristic(nr, nc, new_gems, exit_r, exit_c)
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
            print(f"A* path found in: {len(path)} steps, cost: {f}")
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


def evaluate(grid, sorcerer_r, sorcerer_c, player_r, player_c, gems_left, exit_r, exit_c):
    if (sorcerer_r, sorcerer_c) == (player_r, player_c):
        return CAPTURE_REWARD
    if grid[player_r][player_c] == 'E' and len(gems_left) == 0:
        return -CAPTURE_REWARD
    dist = manhattan_distance(sorcerer_r, sorcerer_c, player_r, player_c)

    # proximity to the player is a negative score, so we want to reward the sorcerer for being closer to the player
    # sorcerer (Max) gain by reducing dist
    # player (Min) gains when close -> flees when threatened
    evade = EVADE_WEIGHT / (dist + 1)

    # len(gems_left) * GEM_COST makes stepping on a gem lower than the score
    # multi_target_heuristic pulls the player to the nearest gem/exit
    goal = W_GOAL * (len(gems_left) * GEM_COST + multi_target_heuristic(player_r, player_c, gems_left, exit_r, exit_c))

    return evade + goal

def minimax(grid, depth, is_maximizing, sorcerer_r, sorcerer_c, player_r, player_c, rows, cols, gems_left, exit_r,
            exit_c):
    if (sorcerer_r, sorcerer_c) == (player_r, player_c): return CAPTURE_REWARD
    if grid[player_r][player_c] == 'E' and len(gems_left) == 0: return -CAPTURE_REWARD

    if is_maximizing:
        # sorcerers turn - collects no gems, gems-left passes through unchanged
        max_eval = float("-inf")
        moves = get_valid_moves(sorcerer_r, sorcerer_c, grid, rows, cols)
        for nr, nc in moves:
            ev = minimax(grid, depth - 1, False, nr, nc, player_r, player_c, rows, cols, gems_left, exit_r, exit_c)
            max_eval = max(max_eval, ev)
        if not moves:  # cornered sorcerer - stay put, let player move
            return minimax(grid, depth - 1, False, sorcerer_r, sorcerer_c, player_r, player_c,
                           rows, cols, gems_left, exit_r, exit_c)
        return max_eval

    else:
        # player's turn  collect any gem landed on, then let the sorcerer reply
        min_eval = float("inf")
        moves = get_valid_moves(player_r, player_c, grid, rows, cols)
        for nr, nc in moves:
            new_gems = tuple(g for g in gems_left if g != (nr, nc)) if (nr, nc) in gems_left else gems_left
            ev = minimax(grid, depth - 1, True, sorcerer_r, sorcerer_c, nr, nc,
                         rows, cols, new_gems, exit_r, exit_c)
            # discourage routing the player through hazard tiles;
            # applied at every ply of the lookahead so a path crossing multiple
            # hazards is penalised more than one crossing a single hazard
            landing_tile = grid[nr][nc]
            if landing_tile == 'M':
                ev += HAZARD_PENALTY_M
            elif landing_tile == 'S':
                ev += HAZARD_PENALTY_S
            min_eval = min(min_eval, ev)

        if not moves:
            return minimax(grid, depth - 1, True, sorcerer_r, sorcerer_c, player_r, player_c,
                           rows, cols, gems_left, exit_r, exit_c)
        return min_eval


def get_best_sorcerer_move(grid, sorcerer_r, sorcerer_c, player_r, player_c, gems_left, exit_r, exit_c, rows, cols,
                           depth=2, avoid=None):
    best_moves = [(sorcerer_r, sorcerer_c)]
    max_eval = float("-inf")

    for nr, nc in get_valid_moves(sorcerer_r, sorcerer_c, grid, rows, cols):
        ev = minimax(grid, depth - 1, False, nr, nc, player_r, player_c, rows, cols, gems_left, exit_r, exit_c)
        # Penalise re-entering a recently occupied cell to break pursuit loops.
        if avoid is not None and (nr, nc) in avoid:
            ev -= REVISIT_PENALTY
        if ev > max_eval:
            max_eval = ev
            best_moves = [(nr, nc)]
        elif ev == max_eval:
            # tie for best score
            best_moves.append((nr, nc))
    return random.choice(best_moves)


def main():
    pygame.init()

    # Settings
    TILE_SIZE = 32  # Scaled up from 16 for better visibility
    NATIVE_TILE = 16  # The actual pixel size of the tiles

    rows, cols = medium_map
    my_map = construct_map(rows, cols)

    # Set up the display
    screen_width = cols * TILE_SIZE
    screen_height = rows * TILE_SIZE
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption('Dungeon Crawler - UCS Agent')

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
        # TODO Bones placeholder as mud
        'S': get_sprite(Dungeon_sprite_sheet, 112, 112, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        # TODO Skeleton placeholder as trap
        'G': get_sprite(Dungeon_sprite_sheet, 96, 128, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        # TODO Coins placeholder instead of gems
        'P': get_sprite(Character_sprite_sheet, 64, 32, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),
        'X': get_sprite(Character_sprite_sheet, 64, 48, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),

        # auto tiling sprites for walls
        'WALL_T': get_sprite(Dungeon_sprite_sheet, 16, 0, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),  # Top Edge
        'WALL_B': get_sprite(Dungeon_sprite_sheet, 16, 64, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),  # Bottom Edge
        'WALL_L': get_sprite(Dungeon_sprite_sheet, 0, 16, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),  # Left Edge
        'WALL_R': get_sprite(Dungeon_sprite_sheet, 80, 16, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),  # Right Edge
        'WALL_TL': get_sprite(Dungeon_sprite_sheet, 0, 0, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),  # Top-Left Corner
        'WALL_TR': get_sprite(Dungeon_sprite_sheet, 80, 0, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),  # Top-Right Corner
        'WALL_BL': get_sprite(Dungeon_sprite_sheet, 0, 64, NATIVE_TILE, NATIVE_TILE, TILE_SIZE),  # Bottom-Left Corner
        'WALL_BR': get_sprite(Dungeon_sprite_sheet, 80, 64, NATIVE_TILE, NATIVE_TILE, TILE_SIZE)  # Bottom-Right Corner
    }

    path = a_star(my_map, rows, cols)

    # Set up a clock to control the animation speed
    clock = pygame.time.Clock()

    player_r, player_c = find_player(my_map, rows, cols)
    my_map[player_r][player_c] = '.'  # erase the player from the static map array

    sorcerer_r, sorcerer_c = rows - 2, cols - 3

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

            if (sorcerer_r, sorcerer_c) != (player_r, player_c):
                sorcerer_r, sorcerer_c = get_best_sorcerer_move(
                    my_map, sorcerer_r, sorcerer_c, player_r, player_c, rows, cols, depth=2
                )
            if (sorcerer_r, sorcerer_c) == (player_r, player_c):
                print("DEATH! The sorcerer caught you.")
                path = []

        # Clears the screen
        screen.fill((0, 0, 0))

        # Draws the map
        for r in range(rows):
            for c in range(cols):
                rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                screen.blit(SPRITES['.'], rect)

                tile_type = my_map[r][c]
                if tile_type != '.':
                    # --- NEW: AUTO-TILING LOGIC ---
                    if tile_type == '#':
                        # Check Corners first
                        if r == 0 and c == 0:
                            sprite_to_draw = SPRITES['WALL_TL']
                        elif r == 0 and c == cols - 1:
                            sprite_to_draw = SPRITES['WALL_TR']
                        elif r == rows - 1 and c == 0:
                            sprite_to_draw = SPRITES['WALL_BL']
                        elif r == rows - 1 and c == cols - 1:
                            sprite_to_draw = SPRITES['WALL_BR']

                        # Check Edges next
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

                            # Draws all other items (M, S, G, E)
                    else:
                        sprite_to_draw = SPRITES.get(tile_type, SPRITES['.'])

                    screen.blit(sprite_to_draw, rect)

                    # Draw player on top
                if r == player_r and c == player_c:
                    screen.blit(SPRITES['P'], rect)
                elif r == sorcerer_r and c == sorcerer_c:
                    screen.blit(SPRITES['X'], rect)

        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
