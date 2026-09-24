import contextlib
import io
import unittest
from unittest.mock import patch

from poker.game import PokerGame


class StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = PokerGame(starting_chips=20, opponents=3, seed=7)
        self.cpu = self.game.cpus[0]

    def test_value_end_of_range_bets(self) -> None:
        with patch.object(self.game, "_cpu_strength", return_value=(0.9, 0.0)), patch.object(
            self.game.rng, "random", return_value=0.5
        ):
            self.assertEqual(self.game._cpu_open_action(self.cpu), "b")

    def test_medium_strength_checks(self) -> None:
        with patch.object(self.game, "_cpu_strength", return_value=(0.52, 0.0)), patch.object(
            self.game.rng, "random", return_value=0.5
        ):
            self.assertEqual(self.game._cpu_open_action(self.cpu), "c")

    def test_weak_end_can_bluff(self) -> None:
        with patch.object(self.game, "_cpu_strength", return_value=(0.2, 0.0)), patch.object(
            self.game.rng, "random", return_value=0.0
        ):
            self.assertEqual(self.game._cpu_open_action(self.cpu), "b")

    def test_multiway_hand_conserves_all_chips(self) -> None:
        total = sum(player.chips for player in self.game.players)
        with patch("builtins.input", return_value="c"), contextlib.redirect_stdout(io.StringIO()):
            self.game._play_hand()
        self.assertEqual(sum(player.chips for player in self.game.players), total)
        self.assertEqual(self.game.pot, 0)

    def test_human_decision_view_repeats_essential_information(self) -> None:
        from poker.cards import Card

        self.game.human.hand = [Card(14, "s"), Card(13, "s")]
        self.game.board = [Card(12, "s"), Card(7, "c"), Card(3, "h")]
        self.game.pot = 24
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.game._print_human_state(call_amount=8)
        text = output.getvalue()
        self.assertIn("[♠A]", text)
        self.assertIn("[♠Q]", text)
        self.assertIn("底池 24", text)
        self.assertIn("跟注需 8", text)
        self.assertIn("底池赔率 25%", text)


if __name__ == "__main__":
    unittest.main()
