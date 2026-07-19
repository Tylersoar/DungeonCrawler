# AI Dungeon Crawler: Search Algorithm Visualiser

Grid-based environment built in Python and Pygame. This project is a testbed for evaluating, and visualizing AI search algorithms and Reinforcement Learning models. 

This repository was developed as a Final Year University Project to explore single-agent pathfinding, multi-objective state space expansion, and multi-agent adversarial game theory.

## Implemented AI Algorithms

### Single-Agent Uninformed Search
* **Breadth-First Search (BFS):** Explores the grid in even layers to find the shortest path (fewest steps) to the exit.
* **Uniform-Cost Search (UCS):** Utilizes a priority queue (`heapq`) to navigate around high-cost hazards (Mud, Spikes) and find the mathematically cheapest path.

### Single-Agent Informed (Heuristic) Search
* **Greedy Best-First Search:** Explores purely based on the Manhattan Distance heuristic to the exit.
* **A* Search (Multi-Objective):** Balances true cost ($g$) with a heuristic estimate ($h$). `(row, col, uncollected_gems)`, allowing the agent to efficiently clear all four corners of the map before navigating to the exit.

## Environment Architecture

The environment relies on a clean Model-View-Controller (MVC) design pattern to prevent continuous physics bugs from impacting the discrete AI mathematical states.
* **The Model:** A lightweight 2D array generated procedurally with random hazard placements.
* **The View:** A Pygame rendering loop that visually interprets the array state at a capped framerate so the algorithms can be observed in real-time.
* **Features:** Impassable walls, dynamic player routing, environmental hazards (Bones, Skulls), and collectable state-altering items (Gems).

