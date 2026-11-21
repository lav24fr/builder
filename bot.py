import math
import mechfight as mf
from navigation import Arena, Navigator
from objective import Objectives
from equipment import Equipment


class Bot:
    name = "Circuit-C"

    def __init__(self, hello):
        self.config = hello["config"]
        self.arena = Arena(hello["map"]["dir"], self.config["mech"])
        self.nav = Navigator(self.arena)
        self.equipment = Equipment(self.arena, self.config)
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
        self.equipment.apply(action, obs, item)
        return action


if __name__ == "__main__":
    mf.run(Bot)
