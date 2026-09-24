from __future__ import annotations

import random
from dataclasses import dataclass

SUITS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
RANKS = {2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K", 14: "A"}


@dataclass(frozen=True, order=True)
class Card:
    rank: int
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANKS or self.suit not in SUITS:
            raise ValueError("invalid card")

    def __str__(self) -> str:
        return f"{SUITS[self.suit]}{RANKS[self.rank]}"


class Deck:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        (rng or random).shuffle(self.cards)

    def deal(self, count: int = 1) -> list[Card]:
        if count > len(self.cards):
            raise ValueError("not enough cards in deck")
        return [self.cards.pop() for _ in range(count)]


def show_cards(cards: list[Card]) -> str:
    return "  ".join(f"[{card}]" for card in cards)
