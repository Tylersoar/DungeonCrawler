import random


def construct_map(rows, cols):
    arr = [['P' for _ in range(cols)] for _ in range(rows)]
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

    return arr


my_map = construct_map(6, 6)
for row in my_map:
    print(row)
