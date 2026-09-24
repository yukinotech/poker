import contextlib
import io
import unittest
from unittest.mock import patch

from poker.cards import Card
from poker.game import BIG_BLIND, DEFAULT_CHIPS, SMALL_BLIND, PokerGame


class BlindTests(unittest.TestCase):
    def test_default_stack_and_blind_level(self) -> None:
        game = PokerGame(opponents=3, seed=1)
        self.assertEqual(game.human.chips, DEFAULT_CHIPS)
        self.assertEqual((SMALL_BLIND, BIG_BLIND), (10, 20))

    def test_multiway_blinds_follow_button(self) -> None:
        game = PokerGame(opponents=3, seed=1)
        game._set_blind_positions(game.players)
        self.assertIs(game.players[game.hand_dealer], game.human)
        self.assertIs(game.small_blind_player, game.cpus[0])
        self.assertIs(game.big_blind_player, game.cpus[1])

    def test_heads_up_button_posts_small_blind(self) -> None:
        game = PokerGame(opponents=1, seed=1)
        game._set_blind_positions(game.players)
        self.assertIs(game.small_blind_player, game.human)
        self.assertIs(game.big_blind_player, game.cpus[0])

    def test_custom_raise_is_matched_and_preserves_chips(self) -> None:
        game = PokerGame(starting_chips=200, opponents=1, seed=1)
        game.human.hand = [Card(14, "s"), Card(13, "s")]
        game.cpus[0].hand = [Card(2, "c"), Card(3, "c")]
        game._set_blind_positions(game.players)
        game._take(game.small_blind_player, SMALL_BLIND)
        game._take(game.big_blind_player, BIG_BLIND)
        with (
            patch("builtins.input", return_value="r 60"),
            patch.object(game, "_cpu_action", return_value=("c", 0)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            game._betting_round(preflop=True)
        self.assertEqual(game.pot, 120)
        self.assertEqual(game.human.street_bet, 60)
        self.assertEqual(game.cpus[0].street_bet, 60)
        self.assertEqual(sum(player.chips for player in game.players) + game.pot, 400)


if __name__ == "__main__":
    unittest.main()
