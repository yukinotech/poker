import contextlib
import io
import unittest
from unittest.mock import patch

from poker.game import PokerGame


class StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = PokerGame(starting_chips=200, opponents=3, seed=7)
        self.cpu = self.game.cpus[0]

    def test_value_end_of_range_bets(self) -> None:
        with patch.object(self.game, "_cpu_strength", return_value=(0.9, 0.0)), patch.object(
            self.game.rng, "random", return_value=0.5
        ):
            action, target = self.game._cpu_action(self.cpu, 0, 0, 20)
        self.assertEqual(action, "r")
        self.assertGreaterEqual(target, 20)

    def test_medium_strength_checks(self) -> None:
        with patch.object(self.game, "_cpu_strength", return_value=(0.52, 0.0)), patch.object(
            self.game.rng, "random", return_value=0.5
        ):
            self.assertEqual(self.game._cpu_action(self.cpu, 0, 0, 20)[0], "c")

    def test_weak_end_can_bluff(self) -> None:
        with patch.object(self.game, "_cpu_strength", return_value=(0.2, 0.0)), patch.object(
            self.game.rng, "random", return_value=0.0
        ):
            self.assertEqual(self.game._cpu_action(self.cpu, 0, 0, 20)[0], "r")

    def test_human_can_choose_custom_raise_size(self) -> None:
        self.game.human.street_bet = 0
        with patch("builtins.input", return_value="r 120"):
            action, target = self.game._human_action(self.game.human, 20, 20, 20)
        self.assertEqual((action, target), ("r", 120))

    def test_compact_raise_without_space_is_accepted(self) -> None:
        with patch("builtins.input", return_value="r100"):
            action, target = self.game._human_action(self.game.human, 20, 20, 20)
        self.assertEqual((action, target), ("r", 100))

    def test_compact_bet_without_space_is_accepted(self) -> None:
        with patch("builtins.input", return_value="b60"):
            action, target = self.game._human_action(self.game.human, 0, 0, 20)
        self.assertEqual((action, target), ("r", 60))

    def test_human_can_go_all_in(self) -> None:
        self.game.human.street_bet = 10
        with patch("builtins.input", return_value="a"):
            action, target = self.game._human_action(self.game.human, 10, 20, 20)
        self.assertEqual(action, "r")
        self.assertEqual(target, 210)

    def test_multiway_hand_conserves_all_chips(self) -> None:
        total = sum(player.chips for player in self.game.players)
        with patch("builtins.input", return_value="c"), contextlib.redirect_stdout(io.StringIO()):
            self.game._play_hand()
        self.assertEqual(sum(player.chips for player in self.game.players), total)
        self.assertEqual(self.game.pot, 0)

    def test_human_decision_view_only_prints_updated_decision_info(self) -> None:
        from poker.cards import Card

        self.game.human.hand = [Card(14, "s"), Card(13, "s")]
        self.game.board = [Card(12, "s"), Card(7, "c"), Card(3, "h")]
        self.game.pot = 24
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.game._print_human_state(call_amount=8)
        text = output.getvalue()
        self.assertNotIn("[♠A]", text)
        self.assertNotIn("[♠Q]", text)
        self.assertIn("轮到你", text)
        self.assertIn("底池 24", text)
        self.assertIn("跟注需 8", text)
        self.assertIn("底池赔率 25%", text)


if __name__ == "__main__":
    unittest.main()
