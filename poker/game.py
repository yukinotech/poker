from __future__ import annotations

import random
from dataclasses import dataclass, field

from .cards import Card, Deck, show_cards
from .evaluator import describe, evaluate


@dataclass
class Player:
    name: str
    chips: int
    is_human: bool = False
    aggression: float = 0.5
    bluff_rate: float = 0.12
    hand: list[Card] = field(default_factory=list)
    folded: bool = False
    contribution: int = 0


def side_pots(players: list[Player]) -> list[tuple[int, list[Player]]]:
    """Return (amount, eligible players) for each main/side pot layer."""
    levels = sorted({player.contribution for player in players if player.contribution > 0})
    pots: list[tuple[int, list[Player]]] = []
    previous = 0
    for level in levels:
        contributors = [player for player in players if player.contribution >= level]
        amount = (level - previous) * len(contributors)
        eligible = [player for player in contributors if not player.folded]
        if amount and eligible:
            pots.append((amount, eligible))
        previous = level
    return pots


class PokerGame:
    """Multi-player, fixed-limit Hold'em with one bet allowed per street."""

    def __init__(self, starting_chips: int = 100, opponents: int = 3, seed: int | None = None) -> None:
        if starting_chips < 10:
            raise ValueError("starting chips must be at least 10")
        if not 1 <= opponents <= 5:
            raise ValueError("opponents must be between 1 and 5")
        self.rng = random.Random(seed)
        self.human = Player("你", starting_chips, is_human=True)
        self.cpus = [
            Player(f"CPU {i}", starting_chips, aggression=self.rng.uniform(0.35, 0.72), bluff_rate=self.rng.uniform(0.07, 0.19))
            for i in range(1, opponents + 1)
        ]
        self.players = [self.human, *self.cpus]
        self.pot = 0
        self.board: list[Card] = []
        self.dealer = 0

    def play(self) -> None:
        self._banner()
        hand_no = 1
        while self.human.chips > 0 and any(cpu.chips > 0 for cpu in self.cpus):
            stacks = " · ".join(f"{p.name} {p.chips}" for p in self.players if p.chips > 0)
            print(f"\n{'─' * 54}\n第 {hand_no} 手牌  |  {stacks}")
            self._play_hand()
            hand_no += 1
            self.dealer = (self.dealer + 1) % len(self.players)
            if self.human.chips and any(cpu.chips > 0 for cpu in self.cpus) and not self._continue():
                break
        if self.human.chips == 0:
            print("\n你已失去全部筹码。CPU 赢得了比赛。")
        elif not any(cpu.chips > 0 for cpu in self.cpus):
            print("\n你清空了所有 CPU 的筹码，赢得比赛！")
        else:
            print("\n游戏结束。" + " · ".join(f"{p.name} {p.chips}" for p in self.players))

    def _play_hand(self) -> None:
        deck = Deck(self.rng)
        self.board, self.pot = [], 0
        live = [p for p in self.players if p.chips > 0]
        for player in self.players:
            player.hand, player.contribution = [], 0
            player.folded = player.chips == 0
        for _ in range(2):
            for player in live:
                player.hand.extend(deck.deal())
        for player in live:
            self._take(player, min(2, player.chips))
        print(f"底注 2  |  {len(live)} 人底池 {self.pot}\n你的手牌  {show_cards(self.human.hand)}")

        streets = (("翻牌前", 0, 4), ("翻牌", 3, 4), ("转牌", 1, 8), ("河牌", 1, 8))
        for name, count, bet in streets:
            if count:
                self.board.extend(deck.deal(count))
            print(f"\n{name}  {show_cards(self.board)}  |  底池 {self.pot}")
            if self._betting_round(bet):
                return
            if len(self._active()) > 1 and all(p.chips == 0 for p in self._active()):
                self.board.extend(deck.deal(5 - len(self.board)))
                print(f"\n所有在池玩家已全下，发完公共牌  {show_cards(self.board)}")
                break
        self._showdown()

    def _betting_round(self, base_bet: int) -> bool:
        order = [p for p in self._seat_order() if not p.folded and p.chips > 0]
        checked: list[Player] = []
        bettor: Player | None = None
        wager = 0
        for player in order:
            if player.is_human:
                action = self._ask("你的行动 [c]过牌  [b]下注: ", {"c", "b"})
            else:
                action = self._cpu_open_action(player)
                if action == "c":
                    print(f"{player.name} 过牌。")
            if action == "b":
                wager = min(base_bet, player.chips)
                self._take(player, wager)
                bettor = player
                print(f"{player.name} 下注 {wager}。")
                break
            checked.append(player)
        if bettor is None:
            return False

        bettor_index = order.index(bettor)
        responders = order[bettor_index + 1 :] + checked
        for player in responders:
            if player.folded or player.chips == 0:
                continue
            call_amount = min(wager, player.chips)
            action = (
                self._ask(f"面对 {wager} 下注 [c]跟注  [f]弃牌: ", {"c", "f"})
                if player.is_human
                else self._cpu_call_action(player, call_amount)
            )
            if action == "f":
                player.folded = True
                print(f"{player.name} 弃牌。")
            else:
                self._take(player, call_amount)
                suffix = "（全下）" if player.chips == 0 else ""
                print(f"{player.name} 跟注 {call_amount}{suffix}。")
            if len(self._active()) == 1:
                self._award_uncontested(self._active()[0])
                return True
        print(f"当前底池 {self.pot}，{len(self._active())} 人在池。")
        return False

    def _cpu_open_action(self, player: Player) -> str:
        strength, draw = self._cpu_strength(player)
        roll = self.rng.random()
        # A polarized range: strong hands bet for value, selected weak/drawing
        # hands bluff, and medium-strength hands mostly check.
        value_threshold = 0.70 - player.aggression * 0.12
        bluff_candidate = strength < 0.34 or (strength < 0.48 and draw > 0)
        value_bet = strength >= value_threshold and roll < 0.72 + player.aggression * 0.22
        bluff = bluff_candidate and roll < player.bluff_rate + draw * 0.35
        return "b" if value_bet or bluff else "c"

    def _cpu_call_action(self, player: Player, call_amount: int) -> str:
        strength, draw = self._cpu_strength(player)
        pot_odds = call_amount / max(1, self.pot + call_amount)
        required = max(0.18, pot_odds - draw - player.aggression * 0.04)
        bluff_catch = self.rng.random() < 0.04 + player.aggression * 0.08
        return "c" if strength >= required or draw >= 0.10 or bluff_catch else "f"

    def _cpu_strength(self, player: Player) -> tuple[float, float]:
        cards = player.hand + self.board
        draw = self._draw_bonus(cards) if self.board else 0.0
        if len(cards) >= 5:
            category = evaluate(cards)[0]
            base = (0.14, 0.38, 0.57, 0.68, 0.76, 0.82, 0.90, 0.97, 1.0)[category]
            opponents = max(1, len(self._active()) - 1)
            return max(0.05, base - 0.025 * (opponents - 1)), draw
        a, b = sorted((card.rank for card in player.hand), reverse=True)
        if a == b:
            return min(0.90, 0.43 + a / 32), draw
        suited = player.hand[0].suit == player.hand[1].suit
        connected = abs(a - b) <= 2
        strength = 0.10 + a / 28 + (0.07 if suited else 0) + (0.06 if connected else 0)
        return min(0.70, strength), draw

    @staticmethod
    def _draw_bonus(cards: list[Card]) -> float:
        suits = [card.suit for card in cards]
        ranks = {card.rank for card in cards}
        if 14 in ranks:
            ranks.add(1)
        flush_draw = any(suits.count(suit) == 4 for suit in set(suits))
        straight_draw = any(len(ranks.intersection(range(start, start + 5))) == 4 for start in range(1, 11))
        return 0.13 * flush_draw + 0.10 * straight_draw

    def _showdown(self) -> None:
        active = self._active()
        scores = {player.name: evaluate(player.hand + self.board) for player in active}
        print("\n摊牌：")
        for player in active:
            print(f"  {player.name:<6} {show_cards(player.hand)}  {describe(scores[player.name])}")
        for index, (amount, eligible) in enumerate(side_pots(self.players)):
            best = max(scores[p.name] for p in eligible)
            winners = [p for p in eligible if scores[p.name] == best]
            share, remainder = divmod(amount, len(winners))
            for winner in winners:
                winner.chips += share
            for winner in winners[:remainder]:
                winner.chips += 1
            label = "主池" if index == 0 else f"边池 {index}"
            print(f"{label} {amount}：{'、'.join(p.name for p in winners)} 赢得。")
        self.pot = 0

    def _active(self) -> list[Player]:
        return [p for p in self.players if p.hand and not p.folded]

    def _seat_order(self) -> list[Player]:
        start = (self.dealer + 1) % len(self.players)
        return self.players[start:] + self.players[:start]

    def _take(self, player: Player, amount: int) -> None:
        amount = min(amount, player.chips)
        player.chips -= amount
        player.contribution += amount
        self.pot += amount

    def _award_uncontested(self, player: Player) -> None:
        print(f"{player.name} 赢得无人争夺的底池 {self.pot}。")
        player.chips += self.pot
        self.pot = 0

    @staticmethod
    def _ask(prompt: str, valid: set[str]) -> str:
        aliases = {"check": "c", "call": "c", "bet": "b", "fold": "f", "过牌": "c", "跟注": "c", "下注": "b", "弃牌": "f"}
        while True:
            try:
                answer = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n已离开牌桌。")
                raise SystemExit(0)
            answer = aliases.get(answer, answer)
            if answer in valid:
                return answer
            print("请输入括号中的选项。")

    @staticmethod
    def _continue() -> bool:
        try:
            return input("\n按 Enter 继续，输入 q 退出: ").strip().lower() != "q"
        except (EOFError, KeyboardInterrupt):
            return False

    @staticmethod
    def _banner() -> None:
        print("♠ ♥ ♦ ♣  P O K E R")
        print("简洁的多人单机德州扑克 · 固定限注")
