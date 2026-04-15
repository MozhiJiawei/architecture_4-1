from __future__ import annotations

from dataclasses import dataclass
import heapq
from math import inf


PORT_CLEARANCE = 18
OBSTACLE_CLEARANCE = 14
GRID_MARGIN = 24
ORTHOGONAL_EPSILON = 1e-3


@dataclass(frozen=True)
class Box:
    id: str
    x: float
    y: float
    width: float
    height: float
    kind: str = "node"

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def expand(self, amount: float) -> "Box":
        return Box(
            id=self.id,
            x=self.x - amount,
            y=self.y - amount,
            width=self.width + (amount * 2),
            height=self.height + (amount * 2),
            kind=self.kind,
        )


@dataclass(frozen=True)
class Port:
    side: str
    ratio: float
    anchor: tuple[float, float]
    waypoint: tuple[float, float]


@dataclass(frozen=True)
class RoutedPath:
    source_port: Port
    target_port: Port
    points: list[tuple[float, float]]


def _interval_overlap(a1: float, a2: float, b1: float, b2: float) -> float:
    low = max(min(a1, a2), min(b1, b2))
    high = min(max(a1, a2), max(b1, b2))
    return high - low


def segment_intersects_box(
    start: tuple[float, float],
    end: tuple[float, float],
    box: Box,
) -> bool:
    x1, y1 = start
    x2, y2 = end
    if abs(x1 - x2) < ORTHOGONAL_EPSILON:
        x = x1
        if box.left < x < box.right:
            return _interval_overlap(y1, y2, box.top, box.bottom) > 0
        return False
    if abs(y1 - y2) < ORTHOGONAL_EPSILON:
        y = y1
        if box.top < y < box.bottom:
            return _interval_overlap(x1, x2, box.left, box.right) > 0
        return False
    segment_left = min(x1, x2)
    segment_right = max(x1, x2)
    segment_top = min(y1, y2)
    segment_bottom = max(y1, y2)
    return not (
        segment_right <= box.left
        or segment_left >= box.right
        or segment_bottom <= box.top
        or segment_top >= box.bottom
    )


def _shared_endpoint(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    return (
        first[0] == second[0]
        or first[0] == second[1]
        or first[1] == second[0]
        or first[1] == second[1]
    )


def segments_conflict(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    (ax1, ay1), (ax2, ay2) = first
    (bx1, by1), (bx2, by2) = second
    first_vertical = abs(ax1 - ax2) < ORTHOGONAL_EPSILON
    second_vertical = abs(bx1 - bx2) < ORTHOGONAL_EPSILON

    if first_vertical and second_vertical:
        if abs(ax1 - bx1) >= 1e-6:
            return False
        overlap = _interval_overlap(ay1, ay2, by1, by2)
        if overlap > 0:
            return True
        return False

    if not first_vertical and not second_vertical:
        if abs(ay1 - by1) >= 1e-6:
            return False
        overlap = _interval_overlap(ax1, ax2, bx1, bx2)
        if overlap > 0:
            return True
        return False

    if first_vertical:
        vertical = first
        horizontal = second
    else:
        vertical = second
        horizontal = first

    (vx1, vy1), (vx2, vy2) = vertical
    (hx1, hy1), (hx2, hy2) = horizontal
    cross_x = vx1
    cross_y = hy1
    on_horizontal = min(hx1, hx2) <= cross_x <= max(hx1, hx2)
    on_vertical = min(vy1, vy2) <= cross_y <= max(vy1, vy2)
    if on_horizontal and on_vertical:
        intersection = (cross_x, cross_y)
        endpoints_first = {first[0], first[1]}
        endpoints_second = {second[0], second[1]}
        if intersection in endpoints_first and intersection in endpoints_second:
            return False
        return True
    return False


def _port(anchor_x: float, anchor_y: float, side: str, ratio: float) -> Port:
    waypoint_x = anchor_x
    waypoint_y = anchor_y
    if side == "left":
        waypoint_x -= PORT_CLEARANCE
    elif side == "right":
        waypoint_x += PORT_CLEARANCE
    elif side == "top":
        waypoint_y -= PORT_CLEARANCE
    elif side == "bottom":
        waypoint_y += PORT_CLEARANCE
    else:
        raise ValueError(f"Unknown side: {side}")
    return Port(side=side, ratio=ratio, anchor=(anchor_x, anchor_y), waypoint=(waypoint_x, waypoint_y))


def _ports_for_box(box: Box) -> list[Port]:
    ratios = (0.25, 0.5, 0.75)
    ports: list[Port] = []
    for ratio in ratios:
        ports.append(_port(box.left, box.top + (box.height * ratio), "left", ratio))
        ports.append(_port(box.right, box.top + (box.height * ratio), "right", ratio))
        ports.append(_port(box.left + (box.width * ratio), box.top, "top", ratio))
        ports.append(_port(box.left + (box.width * ratio), box.bottom, "bottom", ratio))
    return ports


def _preferred_sides(source: Box, target: Box) -> set[str]:
    source_center_x = source.left + (source.width / 2)
    source_center_y = source.top + (source.height / 2)
    target_center_x = target.left + (target.width / 2)
    target_center_y = target.top + (target.height / 2)
    dx = target_center_x - source_center_x
    dy = target_center_y - source_center_y
    preferred: set[str] = set()
    if abs(dx) >= abs(dy):
        preferred.add("right" if dx >= 0 else "left")
        preferred.add("left" if dx >= 0 else "right")
    else:
        preferred.add("bottom" if dy >= 0 else "top")
        preferred.add("top" if dy >= 0 else "bottom")
    if dx >= 0:
        preferred.add("right")
    else:
        preferred.add("left")
    if dy >= 0:
        preferred.add("bottom")
    else:
        preferred.add("top")
    return preferred


def _ordered_ports(source: Box, target: Box) -> list[Port]:
    preferred = _preferred_sides(source, target)
    ports = _ports_for_box(source)
    return sorted(
        ports,
        key=lambda port: (0 if port.side in preferred else 1, abs(port.ratio - 0.5)),
    )


def _candidate_coordinates(
    page_width: float,
    page_height: float,
    obstacles: list[Box],
    source_port: Port,
    target_port: Port,
) -> tuple[list[float], list[float]]:
    xs = {GRID_MARGIN, page_width - GRID_MARGIN, source_port.waypoint[0], target_port.waypoint[0]}
    ys = {GRID_MARGIN, page_height - GRID_MARGIN, source_port.waypoint[1], target_port.waypoint[1]}
    for obstacle in obstacles:
        x_offsets = (
            -OBSTACLE_CLEARANCE * 2,
            -OBSTACLE_CLEARANCE,
            0,
            OBSTACLE_CLEARANCE,
            OBSTACLE_CLEARANCE * 2,
        )
        y_offsets = (
            -OBSTACLE_CLEARANCE * 2,
            -OBSTACLE_CLEARANCE,
            0,
            OBSTACLE_CLEARANCE,
            OBSTACLE_CLEARANCE * 2,
        )
        xs.update(
            {obstacle.left + offset for offset in x_offsets}
            | {obstacle.right + offset for offset in x_offsets}
        )
        ys.update(
            {obstacle.top + offset for offset in y_offsets}
            | {obstacle.bottom + offset for offset in y_offsets}
        )
    return sorted(value for value in xs if 0 <= value <= page_width), sorted(value for value in ys if 0 <= value <= page_height)


def _segment_clear(
    start: tuple[float, float],
    end: tuple[float, float],
    obstacles: list[Box],
    reserved_segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> bool:
    for obstacle in obstacles:
        if segment_intersects_box(start, end, obstacle):
            return False
    candidate = (start, end)
    for reserved in reserved_segments:
        if segments_conflict(candidate, reserved):
            return False
    return True


def _neighbors(
    point: tuple[float, float],
    points: set[tuple[float, float]],
    xs: list[float],
    ys: list[float],
    obstacles: list[Box],
    reserved_segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> list[tuple[tuple[float, float], float]]:
    px, py = point
    result: list[tuple[tuple[float, float], float]] = []
    same_y = [x for x in xs if (x, py) in points]
    same_x = [y for y in ys if (px, y) in points]
    same_y.sort()
    same_x.sort()
    if px in same_y:
        index = same_y.index(px)
        for neighbor_index in (index - 1, index + 1):
            if 0 <= neighbor_index < len(same_y):
                neighbor = (same_y[neighbor_index], py)
                if _segment_clear(point, neighbor, obstacles, reserved_segments):
                    result.append((neighbor, abs(neighbor[0] - px)))
    if py in same_x:
        index = same_x.index(py)
        for neighbor_index in (index - 1, index + 1):
            if 0 <= neighbor_index < len(same_x):
                neighbor = (px, same_x[neighbor_index])
                if _segment_clear(point, neighbor, obstacles, reserved_segments):
                    result.append((neighbor, abs(neighbor[1] - py)))
    return result


def _bend_penalty(
    previous: tuple[float, float] | None,
    current: tuple[float, float],
    nxt: tuple[float, float],
) -> float:
    if previous is None:
        return 0.0
    prev_horizontal = abs(previous[1] - current[1]) < 1e-6
    next_horizontal = abs(current[1] - nxt[1]) < 1e-6
    return 24.0 if prev_horizontal != next_horizontal else 0.0


def _a_star(
    start: tuple[float, float],
    goal: tuple[float, float],
    xs: list[float],
    ys: list[float],
    obstacles: list[Box],
    reserved_segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> list[tuple[float, float]] | None:
    points = {(x, y) for x in xs for y in ys}
    if start not in points or goal not in points:
        return None

    queue: list[tuple[float, float, tuple[float, float], tuple[float, float] | None]] = []
    heapq.heappush(queue, (0.0, 0.0, start, None))
    best_cost: dict[tuple[tuple[float, float], tuple[float, float] | None], float] = {(start, None): 0.0}
    parents: dict[tuple[tuple[float, float], tuple[float, float] | None], tuple[tuple[float, float], tuple[float, float] | None] | None] = {
        (start, None): None
    }
    goal_state: tuple[tuple[float, float], tuple[float, float] | None] | None = None

    while queue:
        _, cost_so_far, point, previous = heapq.heappop(queue)
        state = (point, previous)
        if cost_so_far > best_cost.get(state, inf):
            continue
        if point == goal:
            goal_state = state
            break
        for neighbor, distance in _neighbors(point, points, xs, ys, obstacles, reserved_segments):
            next_cost = cost_so_far + distance + _bend_penalty(previous, point, neighbor)
            next_state = (neighbor, point)
            if next_cost >= best_cost.get(next_state, inf):
                continue
            best_cost[next_state] = next_cost
            parents[next_state] = state
            heuristic = abs(goal[0] - neighbor[0]) + abs(goal[1] - neighbor[1])
            heapq.heappush(queue, (next_cost + heuristic, next_cost, neighbor, point))

    if goal_state is None:
        return None

    reversed_points: list[tuple[float, float]] = []
    current: tuple[tuple[float, float], tuple[float, float] | None] | None = goal_state
    while current is not None:
        reversed_points.append(current[0])
        current = parents[current]
    reversed_points.reverse()
    return _compress_points(reversed_points)


def _compress_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points
    compressed = [points[0]]
    for index in range(1, len(points) - 1):
        prev_point = compressed[-1]
        current = points[index]
        next_point = points[index + 1]
        prev_horizontal = abs(prev_point[1] - current[1]) < 1e-6
        next_horizontal = abs(current[1] - next_point[1]) < 1e-6
        if prev_horizontal == next_horizontal:
            continue
        compressed.append(current)
    compressed.append(points[-1])
    return compressed


def style_for_ports(source_port: Port, target_port: Port) -> str:
    source_anchor = {
        "left": ("0", f"{source_port.ratio:.3f}"),
        "right": ("1", f"{source_port.ratio:.3f}"),
        "top": (f"{source_port.ratio:.3f}", "0"),
        "bottom": (f"{source_port.ratio:.3f}", "1"),
    }
    target_anchor = {
        "left": ("0", f"{target_port.ratio:.3f}"),
        "right": ("1", f"{target_port.ratio:.3f}"),
        "top": (f"{target_port.ratio:.3f}", "0"),
        "bottom": (f"{target_port.ratio:.3f}", "1"),
    }
    exit_x, exit_y = source_anchor[source_port.side]
    entry_x, entry_y = target_anchor[target_port.side]
    return (
        f"exitX={exit_x};exitY={exit_y};exitDx=0;exitDy=0;"
        f"entryX={entry_x};entryY={entry_y};entryDx=0;entryDy=0;"
    )


def route_edge(
    source_box: Box,
    target_box: Box,
    *,
    page_width: float,
    page_height: float,
    obstacles: list[Box],
    reserved_segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> RoutedPath:
    filtered_obstacles = [
        obstacle
        for obstacle in obstacles
        if obstacle.id not in {source_box.id, target_box.id}
    ]

    best_route: RoutedPath | None = None
    best_score = inf
    source_ports = _ordered_ports(source_box, target_box)
    target_ports = _ordered_ports(target_box, source_box)

    for source_port in source_ports[:8]:
        for target_port in target_ports[:8]:
            source_stub = (source_port.anchor, source_port.waypoint)
            target_stub = (target_port.waypoint, target_port.anchor)
            if any(segments_conflict(source_stub, reserved) for reserved in reserved_segments):
                continue
            if any(segments_conflict(target_stub, reserved) for reserved in reserved_segments):
                continue
            xs, ys = _candidate_coordinates(page_width, page_height, filtered_obstacles, source_port, target_port)
            points = _a_star(
                source_port.waypoint,
                target_port.waypoint,
                xs,
                ys,
                filtered_obstacles,
                reserved_segments,
            )
            if not points:
                continue
            score = 0.0
            for start, end in zip(points, points[1:]):
                score += abs(end[0] - start[0]) + abs(end[1] - start[1])
            score += (len(points) - 2) * 24.0
            if score < best_score:
                best_score = score
                best_route = RoutedPath(
                    source_port=source_port,
                    target_port=target_port,
                    points=points,
                )

    if best_route is None:
        raise ValueError(f"No legal orthogonal route found between {source_box.id} and {target_box.id}")
    return best_route
