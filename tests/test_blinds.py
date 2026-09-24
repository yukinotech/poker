import unittest

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


if __name__ == "__main__":
    unittest.main()
