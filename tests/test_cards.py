import random
import unittest

from poker.cards import Card, Deck


class CardTests(unittest.TestCase):
    def test_symbols_and_ranks_are_printed(self) -> None:
        self.assertEqual(str(Card(14, "s")), "♠A")
        self.assertEqual(str(Card(10, "h")), "♥10")

    def test_deck_has_52_unique_cards(self) -> None:
        deck = Deck(random.Random(1))
        self.assertEqual(len(deck.cards), 52)
        self.assertEqual(len(set(deck.cards)), 52)


if __name__ == "__main__":
    unittest.main()
