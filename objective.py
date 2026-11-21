"""Choose nearby game objectives while preserving time to reach the next circle."""
import math


def circle_at(zone, now, future):
    start = max(now, zone["shrink_start"])
    fraction = min(1, max(0, future-start) / max(0.001, zone["shrink_end"]-start))
    center = [a+(b-a)*fraction for a, b in zip(zone["center"], zone["next_center"])]
    return center, zone["radius"] + fraction*(zone["next_radius"]-zone["radius"])


def enough_time(obs, point, distance, wait):
    me, zone, now = obs["self"], obs["zone"], obs["t"]
    speed = me["stats"]["walk_speed"]
    finish = now + distance/speed + wait + 2
    center, radius = circle_at(zone, now, finish)
    if math.dist(point[:2], center) + me["stats"]["radius"] > radius:
        return False
    outside = max(0, math.dist(point[:2], zone["next_center"])-zone["next_radius"])
    return outside == 0 or finish + 1.35*outside/speed + 3 < zone["shrink_end"]


class Objectives:
    def __init__(self, arena, config):
        self.arena = arena
        self.config = config
        self.item = None
        self.recovering = False
        self.avoid_until = {}

    def drop_options(self, obs):
        me = obs["self"]
        result = []
        for drop in obs["drops"]:
            if drop["holder"] not in (None, me["id"]):
                continue
            if any(m["kind"] == "mech" and math.dist(m["pos"][:2], drop["pos"][:2]) <= drop["radius"]
                   for m in obs["mechs"]):
                continue
            travel = math.dist(me["pos"][:2], drop["pos"][:2]) / me["stats"]["walk_speed"]
            if drop["lands_in"] > travel + 2:
                continue
            progress = drop["progress"] if drop["holder"] == me["id"] else 0
            wait = max(0, drop["lands_in"]-travel) + max(0, drop["capture_s"]-progress)
            result.append(("drop", drop, wait))
        return result

    def choose(self, obs, nav, scale):
        now = obs["t"]
        pos = obs["self"]["pos"]
        hp_fraction = obs["self"]["hp"] / obs["self"]["max_hp"]
        self.recovering = hp_fraction < (0.90 if self.recovering else 0.60)
        previous = self.item
        self.item = None
        if not obs["self"]["in_zone"]:
            return
        self.avoid_until = {k:v for k,v in self.avoid_until.items() if v > now}
        choices = []
        options = self.drop_options(obs)
        for kind, obj, wait in options:
            p = obj["pos"]
            d = math.dist(pos[:2], p[:2])
            limit = 85 if kind == "drop" else 45
            if d > limit or obj["id"] in self.avoid_until:
                continue
            if abs(p[2]-self.arena.ground(*p[:2])) > 3.5:
                continue
            node = self.arena.nearest(p, scale)
            if node is None or math.dist(p[:2], self.arena.xy[node]) > self.arena.step*0.71:
                continue
            estimate = 1.35*d
            if previous and previous[1]["id"] == obj["id"]:
                if nav.failed:
                    self.avoid_until[obj["id"]] = now+6
                    continue
                if nav.job is None:
                    estimate = max(d, nav.remaining)
            if estimate > limit*1.4 or not enough_time(obs, p, estimate, wait):
                continue
            rank = d + wait*4 - (6 if previous and previous[1]["id"] == obj["id"] else 0)
            if kind == "drop" and (self.recovering or obj["holder"] == obs["self"]["id"]):
                rank -= 40
            choices.append((rank, obj["id"], kind, obj))
        if choices:
            _, _, kind, obj = min(choices)
            self.item = kind, obj
