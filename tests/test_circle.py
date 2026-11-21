import unittest
from navigation import Navigator


class Grid:
    """Two corridors: the direct entry tile is isolated, the upper tile reachable."""
    step = 6
    xy = [(0,0),(6,0),(12,0),(18,0),(24,0),(6,6),(12,6),(18,6)]
    edges = [ [(1,6,1)], [(0,6,1),(5,6,1)], [], [], [],
              [(1,6,1),(6,6,1)], [(5,6,1),(7,6,1)], [(6,6,1)] ]

    def nearest(self, pos, scale):
        return min(range(len(self.xy)), key=lambda i: sum((a-b)**2 for a,b in zip(pos,self.xy[i])))


class CircleTests(unittest.TestCase):
    def setUp(self):
        self.nav = Navigator(Grid())

    def test_inside_holds_and_new_circle_replans(self):
        self.assertEqual(self.nav.move((0,0),(0,0),1,0,8),[0,0])
        self.assertEqual(self.nav.move((0,0),(24,0),1,1,10),[1,0])

    def test_reachable_entry_around_disconnected_tiles(self):
        for i, pos in enumerate(((0,0),(6,0),(6,6),(12,6))):
            move = self.nav.move(pos,(24,0),1,i/10,10)
            self.assertNotEqual(move,[0,0])
        self.assertEqual(self.nav.end_node,7)
        self.assertEqual(self.nav.move((18,6),(24,0),1,1,10),[0,0])

    def test_point_goal_in_last_circle(self):
        self.assertEqual(self.nav.move((0,0),(6,0),1,0,0),[1,0])
        self.assertEqual(self.nav.move((6,0),(6,0),1,.1,0),[0,0])

    def test_replan_after_leaving_safe_area(self):
        self.nav.move((0,0),(24,0),1,0,10)
        self.nav.move((18,6),(24,0),1,.1,10)
        self.assertEqual(self.nav.move((0,0),(24,0),1,.2,10),[1,0])
