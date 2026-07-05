import random
import pygame
import sys

small_map = 5,5
medium_map = 15,15
large_map = 30,30

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

    arr[1][1] = 'P'

    return arr

def find_player(grid, rows, cols):
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 'P':
                return r, c
    return None, None



def main():
    pygame.init()

    # settings
    TILE_SIZE = 25
    rows, cols = medium_map
    my_map = construct_map(rows, cols)

    # Set up the display
    screen_width = cols * TILE_SIZE
    screen_height = rows * TILE_SIZE
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption('Dungeon Crawler')

    # colour dictionary
    COLORS = {
        '#': (100, 100, 100),  # Wall - Grey
        '.': (30, 30, 30),  # Floor - Dark Grey
        'P': (0, 255, 0),  # Player - Green
        'E': (255, 215, 0)  # Exit - Gold
    }

    # Main game loop
    running = True
    while running:
        # 1. Handles events (Quitting & Input)
        # 1. Handles events (Quitting & Input)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # --- NEW MOVEMENT LOGIC ---
            elif event.type == pygame.KEYDOWN:
                # Find current player coordinates in the array
                pr, pc = find_player(my_map, rows, cols)

                if pr is not None and pc is not None:
                    # Default target coordinates to current position
                    target_r, target_c = pr, pc

                    # Calculate intended target based on key press
                    if event.key == pygame.K_UP:
                        target_r -= 1
                    elif event.key == pygame.K_DOWN:
                        target_r += 1
                    elif event.key == pygame.K_LEFT:
                        target_c -= 1
                    elif event.key == pygame.K_RIGHT:
                        target_c += 1

                    if my_map[target_r][target_c] != '#':

                        # Bonus: Did we hit the exit?
                        if my_map[target_r][target_c] == 'E':
                            print("Success! You reached the stairs.")
                            # For now, we'll just let the player walk over it

                        my_map[pr][pc] = '.'
                        my_map[target_r][target_c] = 'P'

        # 2. Clears the screen
        screen.fill((0, 0, 0))

        # 3. Draws the map
        for r in range(rows):
            for c in range(cols):
                tile_type = my_map[r][c]
                color = COLORS.get(tile_type, (255, 0, 255))

                rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)

                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (50, 50, 50), rect, 1)

        # 4. Updates the display
        pygame.display.flip()

    pygame.quit()
    sys.exit()



if __name__ == '__main__':
    main()