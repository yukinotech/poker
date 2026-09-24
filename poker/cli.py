from __future__ import annotations

import argparse

from .game import PokerGame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="在终端与多个 CPU 玩一局德州扑克")
    parser.add_argument("--chips", type=int, default=2000, help="每位玩家的初始筹码（默认：2000）")
    parser.add_argument("--opponents", type=int, default=3, help="CPU 对手数量，1–5（默认：3）")
    parser.add_argument("--seed", type=int, help="固定随机种子，便于复现牌局")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        PokerGame(starting_chips=args.chips, opponents=args.opponents, seed=args.seed).play()
    except ValueError as error:
        raise SystemExit(f"错误：{error}") from error


if __name__ == "__main__":
    main()
