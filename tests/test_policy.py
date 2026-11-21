import copy
import gzip
import json
import math
import os
from pathlib import Path
import unittest

from bot import Bot
from navigation import Navigator
from objective import Objectives


class Scenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        kit = Path(os.environ.get("MECHFIGHT_KIT", Path(__file__).resolve().parents[2]/"mechfight-kit"))
        with gzip.open(kit/"check/stream.jsonl.gz", "rt") as f:
            hello, cls.sample = json.loads(next(f)), json.loads(next(f))
        hello["map"]["dir"] = str(kit/"arena")
        cls.bot = Bot(hello)
        cls.arena = cls.bot.arena

    def setUp(self):
        self.bot.nav = Navigator(self.arena)
        self.bot.objectives = Objectives(self.arena, self.bot.config)
        self.bot.rest_at = None
        self.bot.equipment.target_id = None
        self.obs = copy.deepcopy(self.sample)
        for key in ("mechs","projectiles","events","drops","cubes","pickups","crates"):
            self.obs[key] = []
        self.me = self.obs["self"]
        # An open game tile, selected independently of the replay's spawn.
        node = self.arena.nearest((310,-270), 1)
        self.point = [*self.arena.xy[node], self.arena.z[node]]
        self.me["pos"] = self.point[:]
        self.obs["zone"].update(center=self.point[:2], next_center=self.point[:2],
                                radius=200, next_radius=100, shrink_start=60, shrink_end=110)
        self.obs["t"] = 5

    def run_route(self, a, b, scale=1):
        nav = self.bot.nav
        nav.move(a, b, scale, 0)
        ticks = 0
        while nav.job is not None and ticks < 400:
            ticks += 1
            nav.move(a, b, scale, ticks/10)
        self.assertIsNone(nav.job)
        self.assertFalse(nav.failed)
        return nav

    def test_obstacle_detour(self):
        a, b = [141.62,-327.09], [201.62,-327.09]
        nav = self.run_route(a,b)
        self.assertTrue(any(abs(self.arena.xy[n][1]-a[1]) > 3 for n in nav.path))
        self.assertTrue(all(self.arena.clearance[n]>=1 for n in nav.path))

    def test_bridge_underpass_and_growth(self):
        a = self.arena
        n = a.nearest((-128.38,-33.09),1)
        self.assertTrue(any(lo-a.z[n] > 9 for lo,_ in a.solids[n]))
        self.assertGreaterEqual(a.clearance[n],1)
        self.assertLess(a.clearance[n],1.5)
        entrances = [node for node,_,clear in a.edges[n] if clear >= 1]
        self.assertTrue(entrances)
        self.assertIn(n,self.run_route(a.xy[entrances[0]],a.xy[n]).path)

    def test_stall_chooses_other_waypoint(self):
        a,b = [141.62,-327.09], [201.62,-327.09]
        nav = self.run_route(a,b)
        old = nav.path[0]
        nav.move(a,b,1,nav.progress_at+2)
        while nav.job is not None:
            nav.move(a,b,1,nav.progress_at+0.1)
        self.assertEqual(nav.blocked,old)
        self.assertTrue(nav.path)
        self.assertNotEqual(nav.path[0],old)

    def test_rooftop_and_upgrade(self):
        x,y,z = self.point
        self.obs["cubes"] = [{"id":5000,"pos":[x,y,z+12]}]
        self.obs["pickups"] = [{"id":8000,"kind":"lightning","pos":[x,y,z+12]}]
        self.obs["offer"] = {"choices":[{"id":"sensors"},{"id":"armor"},{"id":"servos"}]}
        action = self.bot.act(self.obs)
        self.assertEqual(action["pick"],1)
        self.assertNotIn("take",action)
        self.assertIsNone(self.bot.objectives.item)

    def test_cube_and_resource_cutoff(self):
        self.obs["cubes"] = [{"id":5000,"pos":self.point}]
        self.bot.act(self.obs)
        self.assertEqual(self.bot.objectives.item[0],"cube")
        self.me["cubes"] = 3
        self.bot.act(self.obs)
        self.assertIsNone(self.bot.objectives.item)

    def test_shrinking_and_zero_circle(self):
        self.obs["cubes"] = [{"id":5000,"pos":self.point}]
        self.obs["zone"].update(next_center=[self.point[0]-100,self.point[1]],next_radius=0,
                                shrink_start=0,shrink_end=5.1)
        for t in (5,6):
            self.obs["t"] = t
            action = self.bot.act(self.obs)
            self.assertIsNone(self.bot.objectives.item)
            self.assertTrue(action["boost"])
            self.assertTrue(all(math.isfinite(n) for n in action["move"]))

    def test_recovery_and_capture(self):
        self.me["hp"] *= .4
        self.obs["crates"] = [{"id":1000,"pos":self.point,"hp":300}]
        action = self.bot.act(self.obs)
        self.assertIsNone(self.bot.objectives.item)
        self.assertFalse(any(action["fire"]))
        self.obs["drops"] = [{"id":20000,"pos":self.point,"holder":None,"progress":0,
                              "lands_in":0,"capture_s":4,"radius":8}]
        action = self.bot.act(self.obs)
        self.assertEqual(self.bot.objectives.item[0],"drop")
        self.assertEqual(action["move"],[0,0])
        self.obs["drops"][0]["holder"] = 7
        self.bot.act(self.obs)
        self.assertIsNone(self.bot.objectives.item)
        self.obs["drops"][0]["holder"] = None
        self.obs["mechs"] = [{"kind":"mech","id":7,"pos":self.point,"vel":[0,0,0]}]
        self.bot.act(self.obs)
        self.assertIsNone(self.bot.objectives.item)

    def test_equipment_and_empty_magazine(self):
        self.me["weapons"][0]["ammo"] = 0
        self.obs["pickups"] = [{"id":8000,"kind":"lightning","pos":self.point}]
        action = self.bot.act(self.obs)
        self.assertTrue(action["reload"])
        self.assertEqual(action["take"],8000)
        self.assertFalse(any(action["fire"]))


if __name__ == "__main__":
    unittest.main()
