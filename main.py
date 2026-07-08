import random
import pygame
import sys
import heapq

small_map = 5, 5
medium_map = 15, 15
large_map = 30, 30


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

    arr[1][1] = 'P'

    return arr


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

    if exit_r is None:
        print("Error: no exit found on map")
        return None

    # calculates the inital heuristic
    start_h = manhattan_distance(start_r, start_c, exit_r, exit_c)

    pq = [(start_h,0, start_r, start_c, [])]  # priority queue that stores total_cost, current row/col, path so far
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

                    new_f = new_g + new_h

                    move_name = directions[(dr, dc)]
                    new_path = path + [move_name]

                    heapq.heappush(pq, (new_f, new_g, nr, nc, new_path))

    print("No path found")
    return None


def main():
    pygame.init()

    # Settings
    TILE_SIZE = 25
    rows, cols = medium_map
    my_map = construct_map(rows, cols)

    # Set up the display
    screen_width = cols * TILE_SIZE
    screen_height = rows * TILE_SIZE
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption('Dungeon Crawler - UCS Agent')

    COLORS = {
        '#': (100, 100, 100),  # Wall
        '.': (30, 30, 30),  # Floor
        'P': (0, 255, 0),  # Player
        'E': (255, 215, 0),  # Exit
        'M': (139, 69, 19),  # Mud
        'S': (200, 0, 0)  # Spikes
    }

    path = a_star(my_map, rows, cols)

    # Set up a clock to control the animation speed
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # If we have a path, and there are still moves left in it
        if path and len(path) > 0:
            move = path.pop(0)  # Take the very first move off the list

            pr, pc = find_player(my_map, rows, cols)
            target_r, target_c = pr, pc

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
                if my_map[target_r][target_c] == 'E':
                    print("Success! you reached the stairs.")
                    path = []  # Empty the path to stop moving

                my_map[pr][pc] = '.'
                my_map[target_r][target_c] = 'P'

        # Clears the screen
        screen.fill((0, 0, 0))

        # Draws the map
        for r in range(rows):
            for c in range(cols):
                tile_type = my_map[r][c]
                color = COLORS.get(tile_type, (255, 0, 255))
                rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (50, 50, 50), rect, 1)

        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
