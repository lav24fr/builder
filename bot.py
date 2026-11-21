import math
import mechfight as mf
from navigation import Arena, Navigator
from objective import Objectives, enough_time
from equipment import Equipment


class Bot:
    name = "Circuit-D"

    def __init__(self, hello):
        self.config = hello["config"]
        self.arena = Arena(hello["map"]["dir"], self.config["mech"])
        self.nav = Navigator(self.arena)
        self.equipment = Equipment(self.arena, self.config)
        self.objectives = Objectives(self.arena, self.config)

        self.rest_at = None

    def act(self, obs):
        me = obs["self"]
        pos = me["pos"]
        zone = obs["zone"]
        scale = max(me["stats"]["radius"]/self.config["mech"]["radius"],
                    me["stats"]["height"]/self.config["mech"]["height"])
        self.objectives.choose(obs, self.nav, scale)
        item = self.objectives.item
        goal = item[1]["pos"][:2] if item else zone["next_center"]
        nearby_mech = any(m["kind"] == "mech" and math.dist(pos, m["pos"]) <=
                          self.config["vision"]["near_range"] for m in obs["mechs"])
        took_damage = any(e["type"] == "damaged" for e in obs["events"])
        if self.objectives.recovering and not nearby_mech and not took_damage and not item and enough_time(
                obs, pos, 0, self.config["mech"]["regen_delay"] + 2):
            if self.rest_at is None:
                self.rest_at = tuple(pos[:2])
            goal = self.rest_at
        else:
            self.rest_at = None
        move = self.nav.move(pos, goal, scale, obs["t"])
        if item and item[0] == "drop" and math.dist(pos[:2], goal) < item[1]["radius"]*0.7:
            move = [0, 0]
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
        if self.rest_at is not None:
            action["fire"] = [False, False]
        return action


if __name__ == "__main__":
    mf.run(Bot)
