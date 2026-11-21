import math
import mechfight as mf
from navigation import Arena, Navigator


class Bot:
    name = "Circuit-E"

    def __init__(self, hello):
        self.config = hello["config"]
        self.arena = Arena(hello["map"]["dir"], self.config["mech"])
        self.nav = Navigator(self.arena)

    def act(self, obs):
        me = obs["self"]
        pos = me["pos"]
        zone = obs["zone"]
        scale = max(me["stats"]["radius"]/self.config["mech"]["radius"],
                    me["stats"]["height"]/self.config["mech"]["height"])
        goal = zone["next_center"]
        # Leave room for deceleration and the grid's waypoint tolerance.
        arrival_radius = max(0, zone["next_radius"] - self.arena.step - me["stats"]["radius"])
        move = self.nav.move(pos, goal, scale, obs["t"], arrival_radius)
        yaw = math.atan2(move[1], move[0]) if any(move) else me["aim"][0]
        remaining = zone["shrink_end"] - obs["t"]
        outside_next = math.dist(pos[:2], zone["next_center"]) > zone["next_radius"]
        hurry = outside_next and self.nav.remaining / me["stats"]["walk_speed"] + 3 >= remaining
        action = {"move": move, "aim": [yaw, 0], "boost": not me["in_zone"] or hurry}
        if obs["offer"]:
            action["pick"] = 0
        pickups = [p for p in obs["pickups"] if p["kind"] != "gun"
                   and math.dist(p["pos"][:2], pos[:2]) < self.config["loot"]["pickup_radius"]]
        if me["weapons"][1] is None and pickups:
            action["take"] = pickups[0]["id"]
        enemies = [m for m in obs["mechs"] if m["kind"] == "mech"]
        if enemies:
            target = min(enemies, key=lambda m: math.dist(m["pos"], pos))["pos"]
            action["aim"] = [math.atan2(target[1]-pos[1], target[0]-pos[0]),
                             math.atan2(target[2]-pos[2]-2.5, math.dist(pos[:2], target[:2]))]
            action["fire"] = [True, True]
        return action


if __name__ == "__main__":
    mf.run(Bot)
