import unittest

from poker.game import Player, side_pots


class SidePotTests(unittest.TestCase):
    def test_multiway_all_in_creates_main_and_side_pots(self) -> None:
        short = Player("short", 0, contribution=20)
        medium = Player("medium", 0, contribution=50)
        deep = Player("deep", 50, contribution=50)
        pots = side_pots([short, medium, deep])
        self.assertEqual([(n, [p.name for p in e]) for n, e in pots], [
            (60, ["short", "medium", "deep"]),
            (60, ["medium", "deep"]),
        ])

    def test_folded_money_stays_but_player_is_ineligible(self) -> None:
        folded = Player("folded", 50, contribution=50, folded=True)
        a = Player("a", 50, contribution=50)
        b = Player("b", 80, contribution=20)
        pots = side_pots([folded, a, b])
        self.assertEqual([(n, [p.name for p in e]) for n, e in pots], [
            (60, ["a", "b"]),
            (60, ["a"]),
        ])


if __name__ == "__main__":
    unittest.main()
