"""Ground routes over the static game arena. All distances are in game meters."""
from array import array
from collections import deque
from heapq import heappop, heappush
import hashlib
import json
import zlib
import math
from pathlib import Path
import sys
import time


def ring_distance(x, y, ring):
    """Signed distance to the footprint perimeter (negative inside)."""
    inside = False
    best = math.inf
    ax, ay = ring[-2:]
    for i in range(0, len(ring), 2):
        bx, by = ring[i:i + 2]
        dx, dy = bx - ax, by - ay
        if (ay > y) != (by > y) and x < ax + (y - ay) * dx / dy:
            inside = not inside
        length2 = dx * dx + dy * dy
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / length2)) if length2 else 0
        best = min(best, (x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2)
        ax, ay = bx, by
    return math.sqrt(best) * (-1 if inside else 1)


class Arena:
    step = 6

    def __init__(self, directory, mech):
        folder = Path(directory) / "v2"
        world_bytes = (folder / "world.json").read_bytes()
        world = json.loads(world_bytes)
        self.terrain = world["terrain"]
        self.samples = array("h")
        heights = (folder / self.terrain["file"]).read_bytes()
        self.samples.frombytes(heights)
        if sys.byteorder != "little":
            self.samples.byteswap()
        b = world["bounds"]
        self.x0, self.y0 = b["minX"], b["minY"]
        self.width = int((b["maxX"] - self.x0) / self.step) + 1
        self.height = int((b["maxY"] - self.y0) / self.step) + 1
        self.xy = [(self.x0 + i * self.step, self.y0 + j * self.step)
                   for j in range(self.height) for i in range(self.width)]
        # Bind the baked graph to the actual mounted map and live traversal rules.
        signature = [self.step, mech["radius"], mech["height"], mech["step_up"], mech["max_slope_deg"]]
        self.fingerprint = hashlib.sha256(world_bytes + heights + json.dumps(signature).encode()).hexdigest()
        cache = Path(__file__).with_name("ground-grid.zlib")
        if cache.is_file():
            data = json.loads(zlib.decompress(cache.read_bytes()))
            if data["fingerprint"] == self.fingerprint:
                self.z, self.clearance, self.edges = data["z"], data["clearance"], data["edges"]
                self.solids = {int(n): spans for n, spans in data["solids"].items()}
                return
        self.z = [self.ground(x, y) for x, y in self.xy]
        self.clearance = [min(x-self.x0, y-self.y0, b["maxX"]-x, b["maxY"]-y) / mech["radius"]
                          for x, y in self.xy]
        self.solids = {}
        for prism in world["prisms"]:
            ring = prism["ring"]
            # A point outside this margin is over 10 base radii from this solid.
            margin = 10 * mech["radius"] + self.step
            lo = self.indices(min(ring[::2])-margin, min(ring[1::2])-margin)
            hi = self.indices(max(ring[::2])+margin, max(ring[1::2])+margin)
            for j in range(lo[1], hi[1]+1):
                for i in range(lo[0], hi[0]+1):
                    n = j*self.width+i
                    x, y = self.xy[n]
                    d = ring_distance(x, y, ring)
                    for hole in prism["holes"]:
                        d = max(d, -ring_distance(x, y, hole))
                    # Nodes and diagonal links cover a neighborhood around each sample.
                    if d <= self.step * 0.71:
                        self.solids.setdefault(n, []).append((prism["base"], prism["top"]))
                    if prism["top"] > self.z[n] + mech["step_up"]:
                        side = (d-self.step*0.71) / mech["radius"]
                        under = (prism["base"]-self.z[n]) / mech["height"]
                        self.clearance[n] = min(self.clearance[n], max(side, under))
        self.edges = [[] for _ in self.xy]
        slope = math.tan(math.radians(mech["max_slope_deg"]))
        for n, (x, y) in enumerate(self.xy):
            i, j = n % self.width, n // self.width
            for di, dj in ((1,0), (0,1), (1,1), (-1,1)):
                if not (0 <= i+di < self.width and j+dj < self.height):
                    continue
                other = n + dj*self.width + di
                length = self.step * math.hypot(di, dj)
                clearance = min(self.clearance[n], self.clearance[other])
                if di and dj:
                    clearance = min(clearance, self.clearance[n+di], self.clearance[n+dj*self.width])
                if clearance < 1:
                    continue
                last = self.z[n]
                for part in range(1, 5):
                    z = self.ground(x + di*self.step*part/4, y + dj*self.step*part/4)
                    if abs(z-last) > max(mech["step_up"], slope*length/4):
                        break
                    last = z
                else:
                    self.edges[n].append((other, length, clearance))
                    self.edges[other].append((n, length, clearance))

    def ground(self, x, y):
        t = self.terrain
        u = min(t["nx"]-1.000001, max(0, (x-t["minX"])/t["step"]))
        v = min(t["ny"]-1.000001, max(0, (y-t["minY"])/t["step"]))
        i, j = int(u), int(v)
        a, b = u-i, v-j
        k = j*t["nx"]+i
        s = self.samples
        return t["scale"]*((1-b)*(s[k]*(1-a)+s[k+1]*a) + b*(s[k+t["nx"]]*(1-a)+s[k+t["nx"]+1]*a))

    def indices(self, x, y):
        return (max(0, min(self.width-1, round((x-self.x0)/self.step))),
                max(0, min(self.height-1, round((y-self.y0)/self.step))))

    def nearest(self, pos, scale):
        i, j = self.indices(*pos[:2])
        for radius in range(13):
            choices = []
            for row in range(max(0,j-radius), min(self.height,j+radius+1)):
                for col in range(max(0,i-radius), min(self.width,i+radius+1)):
                    if max(abs(col-i), abs(row-j)) != radius:
                        continue
                    n = row*self.width+col
                    if self.clearance[n] >= scale and self.edges[n]:
                        choices.append(n)
            if choices:
                return min(choices, key=lambda n: math.dist(self.xy[n], pos[:2]))
        return None


class Navigator:
    def __init__(self, arena):
        self.arena = arena
        self.key = None
        self.path = deque()
        self.job = None
        self.failed = False
        self.progress_at = 0
        self.progress_pos = None
        self.blocked = None
        self.remaining = 0

    def search(self, start, center, radius, point_node, scale):
        arena = self.arena
        xy = arena.xy
        queue = [(0, 0, start)]
        parent = {start: None}
        cost = {start: 0}
        nearest = start
        target = center if radius else xy[point_node]
        nearest_dist = math.dist(xy[start], target)
        arrived = False
        while queue:
            _, g, n = heappop(queue)
            if g != cost[n]:
                continue
            h = math.dist(xy[n], target)
            if h < nearest_dist:
                nearest, nearest_dist = n, h
            if (radius and h <= radius) or (not radius and n == point_node):
                nearest = n
                arrived = True
                break
            for other, length, clearance in arena.edges[n]:
                if clearance < scale or other == self.blocked:
                    continue
                ng = g + length
                if ng < cost.get(other, math.inf):
                    cost[other], parent[other] = ng, n
                    distance_left = max(0, math.dist(xy[other], target) - radius)
                    heappush(queue, (ng + 1.12*distance_left, ng, other))
            yield
        n = nearest
        self.failed = not arrived
        self.end_node = nearest
        while parent[n] is not None:
            self.path.appendleft(n)
            n = parent[n]
        self.remaining = cost[nearest]

    def move(self, pos, goal, scale, now, arrival_radius=0):
        arena = self.arena
        distance = math.dist(pos[:2], goal)
        if arrival_radius > 0 and distance <= arrival_radius:
            self.key = None
            self.path.clear()
            self.job = None
            self.remaining = 0
            return [0, 0]
        key = (tuple(goal), scale, arrival_radius)
        if self.key != key:
            self.blocked = None
        elif self.progress_pos is not None and now - self.progress_at >= 1.4:
            if self.path and math.dist(pos[:2], self.progress_pos) < 1:
                self.blocked = self.path[0]
                self.key = None
            self.progress_pos = None
        if self.progress_pos is None or self.key != key:
            self.progress_at, self.progress_pos = now, pos[:2]
        if key != self.key:
            self.key = key
            self.path.clear()
            a = arena.nearest(pos, scale)
            b = None if arrival_radius else arena.nearest(goal, scale)
            self.failed = a is None or (arrival_radius == 0 and b is None)
            self.job = None if self.failed else self.search(a, goal, arrival_radius, b, scale)
            self.remaining = max(0, distance-arrival_radius)
            self.end_node = b
        if self.job is not None:
            deadline = time.perf_counter() + 0.002
            for _ in range(384):
                if next(self.job, True) is True:
                    self.job = None
                    break
                if time.perf_counter() >= deadline:
                    break
        while self.path and math.dist(pos[:2], arena.xy[self.path[0]]) < 1.8:
            node = self.path.popleft()
            if self.path:
                self.remaining -= math.dist(arena.xy[node], arena.xy[self.path[0]])
        if self.path:
            dest = arena.xy[self.path[0]]
        elif self.job is None and not self.failed and self.end_node is not None:
            end = arena.xy[self.end_node]
            dest = goal if not arrival_radius and math.dist(end, goal) <= arena.step*0.71 else end
        else:
            return [0, 0]
        dx, dy = dest[0]-pos[0], dest[1]-pos[1]
        length = math.hypot(dx, dy)
        if length < 0.55:
            self.remaining = 0
            return [0, 0]
        return [dx/max(1, length), dy/max(1, length)]
