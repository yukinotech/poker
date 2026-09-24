from __future__ import annotations

import random
from dataclasses import dataclass, field

from .cards import Card, Deck, show_cards
from .evaluator import describe, evaluate

SMALL_BLIND = 10
BIG_BLIND = 20
SMALL_BET = 20
BIG_BET = 40
DEFAULT_CHIPS = 2000


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
    street_bet: int = 0


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

    def __init__(self, starting_chips: int = DEFAULT_CHIPS, opponents: int = 3, seed: int | None = None) -> None:
        if starting_chips < BIG_BET:
            raise ValueError(f"starting chips must be at least {BIG_BET}")
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
        self.hand_dealer = 0
        self.small_blind_player = self.human
        self.big_blind_player = self.cpus[0]

    def play(self) -> None:
        self._banner()
        hand_no = 1
        while self.human.chips > 0 and any(cpu.chips > 0 for cpu in self.cpus):
            stacks = " · ".join(f"{p.name} {p.chips}" for p in self.players if p.chips > 0)
            print(f"\n{'─' * 54}\n第 {hand_no} 手牌  |  {stacks}")
            self._play_hand()
            hand_no += 1
            self.dealer = (self.hand_dealer + 1) % len(self.players)
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
            player.hand, player.contribution, player.street_bet = [], 0, 0
            player.folded = player.chips == 0
        for _ in range(2):
            for player in live:
                player.hand.extend(deck.deal())
        self._set_blind_positions(live)
        small_paid = min(SMALL_BLIND, self.small_blind_player.chips)
        big_paid = min(BIG_BLIND, self.big_blind_player.chips)
        self._take(self.small_blind_player, small_paid)
        self._take(self.big_blind_player, big_paid)
        print(
            f"级别 {SMALL_BLIND}/{BIG_BLIND}  |  庄家 {self.players[self.hand_dealer].name}  |  "
            f"小盲 {self.small_blind_player.name} {small_paid}  |  大盲 {self.big_blind_player.name} {big_paid}"
        )

        streets = (
            ("翻牌前", 0, SMALL_BET, True),
            ("翻牌", 3, SMALL_BET, False),
            ("转牌", 1, BIG_BET, False),
            ("河牌", 1, BIG_BET, False),
        )
        for name, count, bet, preflop in streets:
            if not preflop:
                for player in self.players:
                    player.street_bet = 0
            if count:
                self.board.extend(deck.deal(count))
            self._print_table(name)
            hand_over = self._preflop_round() if preflop else self._betting_round(bet)
            if hand_over:
                return
            if len(self._active()) > 1 and all(p.chips == 0 for p in self._active()):
                self.board.extend(deck.deal(5 - len(self.board)))
                print(f"\n所有在池玩家已全下，发完公共牌  {show_cards(self.board)}")
                break
        self._showdown()

    def _betting_round(self, base_bet: int) -> bool:
        order = [p for p in self._seat_order() if not p.folded and p.chips > 0]
        checked: list[Player] = []
        announced_checks = 0
        bettor: Player | None = None
        wager = 0
        for player in order:
            if player.is_human:
                self._announce_checks(checked[announced_checks:])
                announced_checks = len(checked)
                self._print_human_state()
                action = self._ask("你的行动 [c]过牌  [b]下注: ", {"c", "b"})
            else:
                action = self._cpu_open_action(player)
            if action == "b":
                self._announce_checks(checked[announced_checks:])
                wager = min(base_bet, player.chips)
                self._take(player, wager)
                bettor = player
                print(f"{player.name} 下注 {wager}。")
                break
            checked.append(player)
        if bettor is None:
            self._announce_checks(checked[announced_checks:])
            print(f"本轮无人下注，底池保持 {self.pot}。")
            return False

        bettor_index = order.index(bettor)
        responders = order[bettor_index + 1 :] + checked
        return self._resolve_wager(bettor, wager, responders)

    def _preflop_round(self) -> bool:
        wager = max(player.street_bet for player in self._active())
        bettor = max(self._active(), key=lambda player: player.street_bet)
        order = self._seat_order(after=self.players.index(self.big_blind_player))
        responders = [player for player in order if player is not bettor and not player.folded and player.chips > 0]
        return self._resolve_wager(bettor, wager, responders)

    def _resolve_wager(self, bettor: Player, wager: int, responders: list[Player]) -> bool:
        cpu_calls: list[str] = []
        cpu_folds: list[str] = []
        for player in responders:
            if player.folded or player.chips == 0:
                continue
            call_amount = min(max(0, wager - player.street_bet), player.chips)
            if call_amount == 0:
                continue
            if player.is_human:
                self._announce_responses(cpu_calls, cpu_folds)
                cpu_calls, cpu_folds = [], []
                self._print_human_state(call_amount)
                action = self._ask(f"面对 {wager} 下注 [c]跟注  [f]弃牌: ", {"c", "f"})
            else:
                action = self._cpu_call_action(player, call_amount)
            if action == "f":
                player.folded = True
                if player.is_human:
                    print("你弃牌。")
                else:
                    cpu_folds.append(player.name)
            else:
                self._take(player, call_amount)
                suffix = "（全下）" if player.chips == 0 else ""
                if player.is_human:
                    print(f"你跟注 {call_amount}{suffix}，底池更新为 {self.pot}。")
                else:
                    cpu_calls.append(f"{player.name}{suffix}")
            if len(self._active()) == 1:
                self._announce_responses(cpu_calls, cpu_folds)
                self._award_uncontested(self._active()[0])
                return True
        self._announce_responses(cpu_calls, cpu_folds)
        print(f"本轮结束：底池 {self.pot} · {len(self._active())} 人在池。")
        return False

    def _print_table(self, street: str) -> None:
        board = show_cards(self.board) if self.board else "—"
        print(f"\n┌─ {street} {'─' * max(1, 42 - len(street))}")
        print(f"│ 公共牌  {board}")
        print(f"│ 你的牌  {show_cards(self.human.hand)}  ·  {self._human_hand_label()}")
        print(f"└─ 底池 {self.pot} · 你的筹码 {self.human.chips} · {len(self._active())} 人在池")

    def _print_human_state(self, call_amount: int | None = None) -> None:
        board = show_cards(self.board) if self.board else "—"
        cost = ""
        if call_amount is not None:
            pot_odds = call_amount / (self.pot + call_amount)
            cost = f" · 跟注需 {call_amount} · 底池赔率 {pot_odds:.0%}"
        print(f"  你的牌 {show_cards(self.human.hand)}（{self._human_hand_label()}） |  公共牌 {board}")
        print(f"  底池 {self.pot} · 你的筹码 {self.human.chips} · {len(self._active())} 人在池{cost}")

    def _human_hand_label(self) -> str:
        if len(self.human.hand) + len(self.board) >= 5:
            return describe(evaluate(self.human.hand + self.board))
        first, second = self.human.hand
        if first.rank == second.rank:
            return "口袋对子"
        if first.suit == second.suit:
            return "同花起手牌"
        if abs(first.rank - second.rank) <= 2:
            return "连张起手牌"
        return "高牌起手牌"

    @staticmethod
    def _announce_checks(players: list[Player]) -> None:
        cpus = [player for player in players if not player.is_human]
        if len(cpus) == 1:
            print(f"{cpus[0].name} 过牌。")
        elif cpus:
            print(f"{len(cpus)} 位 CPU 过牌。")

    @staticmethod
    def _announce_responses(calls: list[str], folds: list[str]) -> None:
        parts: list[str] = []
        if calls:
            parts.append(f"{'、'.join(calls)} 跟注")
        if folds:
            parts.append(f"{'、'.join(folds)} 弃牌")
        if parts:
            print("；".join(parts) + "。")

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

    def _seat_order(self, after: int | None = None) -> list[Player]:
        start = ((self.hand_dealer if after is None else after) + 1) % len(self.players)
        return self.players[start:] + self.players[:start]

    def _set_blind_positions(self, live: list[Player]) -> None:
        live_indices = {self.players.index(player) for player in live}
        self.hand_dealer = next(
            index % len(self.players)
            for index in range(self.dealer, self.dealer + len(self.players))
            if index % len(self.players) in live_indices
        )

        def next_live(after: int) -> int:
            return next(
                index % len(self.players)
                for index in range(after + 1, after + 1 + len(self.players))
                if index % len(self.players) in live_indices
            )

        if len(live) == 2:
            small_index = self.hand_dealer
            big_index = next_live(self.hand_dealer)
        else:
            small_index = next_live(self.hand_dealer)
            big_index = next_live(small_index)
        self.small_blind_player = self.players[small_index]
        self.big_blind_player = self.players[big_index]

    def _take(self, player: Player, amount: int) -> None:
        amount = min(amount, player.chips)
        player.chips -= amount
        player.contribution += amount
        player.street_bet += amount
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
        print(f"简洁的多人单机德州扑克 · {SMALL_BLIND}/{BIG_BLIND} 固定限注")
