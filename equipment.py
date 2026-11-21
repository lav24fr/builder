"""Game inventory and trigger decisions for the mechfight/1 arena."""
import math


class Equipment:
    def __init__(self, arena, config):
        self.arena = arena
        self.config = config
        self.target_id = None

    def clear(self, start, end):
        # The game's short-lived tracking memory includes mechs behind solids.
        distance = math.dist(start[:2], end[:2])
        count = max(1, math.ceil(distance / (self.arena.step/2)))
        for i in range(1, count):
            t = i/count
            x, y, z = (a+(b-a)*t for a,b in zip(start, end))
            col, row = self.arena.indices(x,y)
            cell = row*self.arena.width + col
            if z <= self.arena.z[cell]+5 and z <= self.arena.ground(x,y):
                return False
            for low, high in self.arena.solids.get(cell, ()):
                if low <= z <= high:
                    return False
        return True

    def apply(self, action, obs, item):
        me = obs["self"]
        pos = me["pos"]
        gun, second = me["weapons"]
        action["fire"] = [False, False]
        if second is None:
            pickups = [p for p in obs["pickups"] if p["kind"] == "lightning"
                       and abs(p["pos"][2]-pos[2]) <= 4
                       and math.dist(p["pos"][:2], pos[:2]) <= self.config["loot"]["pickup_radius"]]
            if pickups:
                action["take"] = min(pickups, key=lambda p: math.dist(p["pos"],pos))["id"]
        if not gun or gun["kind"] != "gun":
            return
        stats = gun["stats"]
        muzzle = (pos[0], pos[1], pos[2]+me["stats"]["muzzle_height"])
        mechs = sorted((m for m in obs["mechs"] if m["kind"] == "mech"),
                       key=lambda m: math.dist(m["pos"],pos) * (0.8 if m["id"] == self.target_id else 1))
        candidates = [(m, False) for m in mechs[:3]]
        if item and item[0] == "crate":
            candidates.append((item[1], True))
        self.target_id = None
        for obj, crate in candidates:
            p = obj["pos"]
            height = self.config["crates"]["height"] if crate else (
                self.config["mech"]["height"]*(1+obj.get("cubes",0)*self.config["cubes"]["size_per_cube"]))
            midpoint = (p[0], p[1], p[2]+height/2)
            distance = math.dist(muzzle, midpoint)
            if distance > stats["range"] or not self.clear(muzzle, midpoint):
                continue
            velocity = obj.get("vel", (0,0,0))
            flight = distance / stats["speed"]
            dx, dy, dz = (b + v*flight - a for a,b,v in zip(muzzle, midpoint, velocity))
            yaw, pitch = math.atan2(dy,dx), math.atan2(dz,math.hypot(dx,dy))
            action["aim"] = [yaw, pitch]
            yaw_error = abs(math.remainder(me["aim"][0]-yaw, math.tau))
            pitch_error = abs(me["aim"][1]-pitch)
            radius = self.config["crates"]["radius"] if crate else height*self.config["mech"]["radius"]/self.config["mech"]["height"]
            tolerance = math.atan2(radius, max(distance,1))
            aligned = yaw_error <= tolerance+0.045 and pitch_error <= tolerance+0.045
            action["fire"][0] = aligned and gun["ammo"] > 0 and gun["reload"] <= 0 and gun["cooldown"] <= 0.1
            if not crate:
                self.target_id = obj["id"]
                if second and second["kind"] == "lightning":
                    arc = second["stats"]
                    action["fire"][1] = (distance <= arc["range"] and yaw_error < math.radians(arc["cone_deg"])/2
                                         and second["cooldown"] <= 0.1 and me["energy"] >= arc["energy"])
            break
        if gun["reload"] <= 0 and (gun["ammo"] == 0 or
                (self.target_id is None and gun["ammo"] <= stats["mag"]//2)):
            action["reload"] = True
