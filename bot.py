import math
import mechfight as mf
from navigation import Arena, Navigator


class Bot:
    name = "Circuit-F"

    def __init__(self, hello):
        self.config = hello["config"]
        self.arena = Arena(hello["map"]["dir"], self.config["mech"])
        self.nav = Navigator(self.arena)
        self.jetting = False

    def act(self, obs):
        me = obs["self"]
        pos = me["pos"]
        zone = obs["zone"]
        scale = max(me["stats"]["radius"]/self.config["mech"]["radius"],
                    me["stats"]["height"]/self.config["mech"]["height"])
        goal = zone["next_center"]
        move = self.nav.move(pos, goal, scale, obs["t"])
        # A jump and a held boost are separate mechfight actions. Recharge between flights.
        energy = me["energy"] / me["max_energy"]
        jump = me["grounded"] and energy >= .94
        if me["grounded"]:
            self.jetting = jump
        if energy < .15:
            self.jetting = False
        if not me["grounded"]:
            dx, dy = goal[0]-pos[0], goal[1]-pos[1]
            distance = math.hypot(dx, dy)
            move = [dx/max(1,distance), dy/max(1,distance)]
        yaw = math.atan2(move[1], move[0]) if any(move) else me["aim"][0]
        remaining = zone["shrink_end"] - obs["t"]
        outside_next = math.dist(pos[:2], zone["next_center"]) > zone["next_radius"]
        hurry = outside_next and self.nav.remaining / me["stats"]["walk_speed"] + 3 >= remaining
        ground_sprint = me["grounded"] and (not me["in_zone"] or hurry)
        action = {"move": move, "aim": [yaw, 0], "jump": jump, "boost": self.jetting or ground_sprint}
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
