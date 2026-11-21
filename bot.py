import math
import mechfight as mf
from navigation import Arena, Navigator
from objective import Objectives


class Bot:
    name = "Circuit-B"

    def __init__(self, hello):
        self.config = hello["config"]
        self.arena = Arena(hello["map"]["dir"], self.config["mech"])
        self.nav = Navigator(self.arena)
        self.objectives = Objectives(self.arena, self.config)

    def act(self, obs):
        me = obs["self"]
        pos = me["pos"]
        zone = obs["zone"]
        scale = max(me["stats"]["radius"]/self.config["mech"]["radius"],
                    me["stats"]["height"]/self.config["mech"]["height"])
        self.objectives.choose(obs, self.nav, scale)
        item = self.objectives.item
        goal = item[1]["pos"][:2] if item else zone["next_center"]
        move = self.nav.move(pos, goal, scale, obs["t"])
        yaw = math.atan2(move[1], move[0]) if any(move) else me["aim"][0]
        remaining = zone["shrink_end"] - obs["t"]
        outside_next = math.dist(pos[:2], zone["next_center"]) > zone["next_radius"]
        hurry = outside_next and self.nav.remaining / me["stats"]["walk_speed"] + 3 >= remaining
        action = {"move": move, "aim": [yaw, 0], "boost": not me["in_zone"] or hurry}
        if obs["offer"]:
            priority = {"armor": 0, "plating": 1, "servos": 2}
            choices = obs["offer"]["choices"]
            action["pick"] = min(range(len(choices)), key=lambda i: priority.get(choices[i]["id"], 3))
        pickups = [p for p in obs["pickups"] if p["kind"] != "gun"
                   and abs(p["pos"][2]-pos[2]) <= 4
                   and math.dist(p["pos"][:2], pos[:2]) < self.config["loot"]["pickup_radius"]]
        if me["weapons"][1] is None and pickups:
            action["take"] = pickups[0]["id"]
        enemies = [m for m in obs["mechs"] if m["kind"] == "mech"]
        if enemies:
            target = min(enemies, key=lambda m: math.dist(m["pos"], pos))["pos"]
            action["aim"] = [math.atan2(target[1]-pos[1], target[0]-pos[0]),
                             math.atan2(target[2]-pos[2]-2.5, math.dist(pos[:2], target[:2]))]
            action["fire"] = [True, True]
        elif item and item[0] == "crate":
            x, y, z = item[1]["pos"]
            action["aim"] = [math.atan2(y-pos[1], x-pos[0]), math.atan2(
                z + self.config["crates"]["height"]/2-pos[2]-me["stats"]["muzzle_height"],
                math.hypot(x-pos[0], y-pos[1]))]
            action["fire"] = [True, False]
        return action


if __name__ == "__main__":
    mf.run(Bot)
