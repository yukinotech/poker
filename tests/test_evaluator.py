import unittest

from poker.cards import Card
from poker.evaluator import describe, evaluate


def cards(spec: str) -> list[Card]:
    rank_map = {**{str(value): value for value in range(2, 10)}, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
    return [Card(rank_map[token[0]], token[1]) for token in spec.split()]


class EvaluatorTests(unittest.TestCase):
    def test_straight_flush_beats_quads(self) -> None:
        straight_flush = evaluate(cards("9s Ts Js Qs Ks 2d 3c"))
        quads = evaluate(cards("As Ah Ad Ac Ks 2d 3c"))
        self.assertGreater(straight_flush, quads)
        self.assertEqual(describe(straight_flush), "同花顺")

    def test_wheel_is_five_high_straight(self) -> None:
        score = evaluate(cards("As 2h 3d 4c 5s Kh Qh"))
        self.assertEqual(score, (4, 5))

    def test_best_five_are_selected_from_seven(self) -> None:
        score = evaluate(cards("Ah Ad Kc Ks Qh 2d 3c"))
        self.assertEqual(score[:3], (2, 14, 13))

    def test_pair_kickers_break_tie(self) -> None:
        ace_kicker = evaluate(cards("9s 9h As Kd 7c 3h 2s"))
        queen_kicker = evaluate(cards("9d 9c Qs Jd 7h 3c 2d"))
        self.assertGreater(ace_kicker, queen_kicker)


if __name__ == "__main__":
    unittest.main()
