from __future__ import annotations

from collections import Counter
from itertools import combinations

from .cards import Card

CATEGORY_NAMES = (
    "高牌",
    "一对",
    "两对",
    "三条",
    "顺子",
    "同花",
    "葫芦",
    "四条",
    "同花顺",
)


def evaluate_five(cards: tuple[Card, ...]) -> tuple[int, ...]:
    """Return a lexicographically comparable score for exactly five cards."""
    if len(cards) != 5:
        raise ValueError("evaluate_five requires exactly five cards")

    ranks = sorted((card.rank for card in cards), reverse=True)
    counts = Counter(ranks)
    groups = sorted(((count, rank) for rank, count in counts.items()), reverse=True)
    flush = len({card.suit for card in cards}) == 1
    unique = sorted(set(ranks), reverse=True)
    if unique == [14, 5, 4, 3, 2]:
        straight_high = 5
    else:
        straight_high = unique[0] if len(unique) == 5 and unique[0] - unique[-1] == 4 else 0

    if flush and straight_high:
        return (8, straight_high)
    if groups[0][0] == 4:
        return (7, groups[0][1], groups[1][1])
    if groups[0][0] == 3 and groups[1][0] == 2:
        return (6, groups[0][1], groups[1][1])
    if flush:
        return (5, *ranks)
    if straight_high:
        return (4, straight_high)
    if groups[0][0] == 3:
        kickers = sorted((rank for rank in ranks if rank != groups[0][1]), reverse=True)
        return (3, groups[0][1], *kickers)
    pairs = sorted((rank for count, rank in groups if count == 2), reverse=True)
    if len(pairs) == 2:
        kicker = next(rank for rank in ranks if rank not in pairs)
        return (2, *pairs, kicker)
    if len(pairs) == 1:
        kickers = sorted((rank for rank in ranks if rank != pairs[0]), reverse=True)
        return (1, pairs[0], *kickers)
    return (0, *ranks)


def evaluate(cards: list[Card]) -> tuple[int, ...]:
    if not 5 <= len(cards) <= 7:
        raise ValueError("evaluation requires five to seven cards")
    return max(evaluate_five(combo) for combo in combinations(cards, 5))


def describe(score: tuple[int, ...]) -> str:
    return CATEGORY_NAMES[score[0]]
