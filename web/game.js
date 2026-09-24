"use strict";

const SMALL_BLIND = 10;
const BIG_BLIND = 20;
const SUITS = { s: "♠", h: "♥", d: "♦", c: "♣" };
const RANKS = { 11: "J", 12: "Q", 13: "K", 14: "A" };
const STREET_NAMES = ["翻牌前", "翻牌", "转牌", "河牌"];
const HAND_NAMES = ["高牌", "一对", "两对", "三条", "顺子", "同花", "葫芦", "四条", "同花顺"];

function makeDeck() {
  const deck = [];
  for (const suit of Object.keys(SUITS)) {
    for (let rank = 2; rank <= 14; rank += 1) deck.push({ rank, suit });
  }
  for (let i = deck.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

function compareScores(a, b) {
  const length = Math.max(a.length, b.length);
  for (let i = 0; i < length; i += 1) {
    const difference = (a[i] || 0) - (b[i] || 0);
    if (difference) return difference;
  }
  return 0;
}

function combinations(cards, count) {
  const result = [];
  function choose(start, picked) {
    if (picked.length === count) {
      result.push(picked.slice());
      return;
    }
    for (let i = start; i <= cards.length - (count - picked.length); i += 1) {
      picked.push(cards[i]);
      choose(i + 1, picked);
      picked.pop();
    }
  }
  choose(0, []);
  return result;
}

function evaluateFive(cards) {
  const ranks = cards.map((card) => card.rank).sort((a, b) => b - a);
  const counts = new Map();
  ranks.forEach((rank) => counts.set(rank, (counts.get(rank) || 0) + 1));
  const groups = [...counts.entries()].map(([rank, count]) => [count, rank])
    .sort((a, b) => b[0] - a[0] || b[1] - a[1]);
  const flush = new Set(cards.map((card) => card.suit)).size === 1;
  const unique = [...new Set(ranks)].sort((a, b) => b - a);
  let straightHigh = 0;
  if (unique.join(",") === "14,5,4,3,2") straightHigh = 5;
  else if (unique.length === 5 && unique[0] - unique[4] === 4) straightHigh = unique[0];
  if (flush && straightHigh) return [8, straightHigh];
  if (groups[0][0] === 4) return [7, groups[0][1], groups[1][1]];
  if (groups[0][0] === 3 && groups[1][0] === 2) return [6, groups[0][1], groups[1][1]];
  if (flush) return [5, ...ranks];
  if (straightHigh) return [4, straightHigh];
  if (groups[0][0] === 3) return [3, groups[0][1], ...ranks.filter((rank) => rank !== groups[0][1])];
  const pairs = groups.filter(([count]) => count === 2).map(([, rank]) => rank).sort((a, b) => b - a);
  if (pairs.length === 2) return [2, pairs[0], pairs[1], ranks.find((rank) => !pairs.includes(rank))];
  if (pairs.length === 1) return [1, pairs[0], ...ranks.filter((rank) => rank !== pairs[0])];
  return [0, ...ranks];
}

function evaluate(cards) {
  return combinations(cards, 5).map(evaluateFive).sort((a, b) => compareScores(b, a))[0];
}

function cardText(card) {
  return `${SUITS[card.suit]}${RANKS[card.rank] || card.rank}`;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function roundToBlind(value) {
  return Math.max(BIG_BLIND, Math.round(value / 10) * 10);
}

class PokerGame {
  constructor() {
    this.ui = {
      seats: document.querySelector("#seats"),
      board: document.querySelector("#board"),
      pot: document.querySelector("#pot"),
      street: document.querySelector("#street-label"),
      handNumber: document.querySelector("#hand-number"),
      message: document.querySelector("#table-message"),
      decision: document.querySelector("#decision-text"),
      odds: document.querySelector("#odds-text"),
      sizing: document.querySelector("#sizing"),
      slider: document.querySelector("#bet-slider"),
      amount: document.querySelector("#bet-amount"),
      fold: document.querySelector("#fold"),
      checkCall: document.querySelector("#check-call"),
      betRaise: document.querySelector("#bet-raise"),
      allIn: document.querySelector("#all-in"),
      nextHand: document.querySelector("#next-hand"),
      log: document.querySelector("#action-log"),
      opponents: document.querySelector("#opponent-count"),
      chips: document.querySelector("#starting-chips"),
      buyIns: document.querySelector("#buy-in-count"),
    };
    this.generation = 0;
    this.bindEvents();
    this.newGame();
  }

  bindEvents() {
    document.querySelector("#new-game").addEventListener("click", () => this.newGame());
    document.querySelector("#clear-log").addEventListener("click", () => { this.ui.log.innerHTML = ""; });
    this.ui.slider.addEventListener("input", () => { this.ui.amount.value = this.ui.slider.value; });
    this.ui.amount.addEventListener("input", () => {
      this.ui.slider.value = clamp(Number(this.ui.amount.value), Number(this.ui.slider.min), Number(this.ui.slider.max));
    });
    document.querySelectorAll("[data-size]").forEach((button) => {
      button.addEventListener("click", () => this.setQuickSize(Number(button.dataset.size)));
    });
    this.ui.fold.addEventListener("click", () => this.submitHuman("fold"));
    this.ui.checkCall.addEventListener("click", () => this.submitHuman("call"));
    this.ui.betRaise.addEventListener("click", () => this.submitHuman("raise", Number(this.ui.amount.value)));
    this.ui.allIn.addEventListener("click", () => this.submitHuman("raise", this.human.streetBet + this.human.chips));
    this.ui.nextHand.addEventListener("click", () => this.startNextHand());
  }

  newGame() {
    this.generation += 1;
    const opponentCount = clamp(Number(this.ui.opponents.value) || 3, 1, 5);
    const startingChips = Math.max(200, Number(this.ui.chips.value) || 2000);
    this.startingChips = startingChips;
    this.maxBuyIns = clamp(Number(this.ui.buyIns.value) || 3, 1, 5);
    this.players = [{ id: 0, name: "你", human: true, chips: startingChips, buyInsUsed: 1 }];
    for (let i = 1; i <= opponentCount; i += 1) {
      this.players.push({
        id: i,
        name: `CPU ${i}`,
        human: false,
        chips: startingChips,
        aggression: 0.35 + Math.random() * 0.4,
        bluffRate: 0.06 + Math.random() * 0.14,
        buyInsUsed: 1,
      });
    }
    this.human = this.players[0];
    this.dealer = 0;
    this.handNumber = 0;
    this.street = undefined;
    this.ui.log.innerHTML = "";
    this.log("新游戏开始 · 盲注 10/20", "system");
    this.startNextHand(true);
  }

  startNextHand(first = false) {
    if (!first) {
      if (!this.canContinueMatch()) {
        this.newGame();
        return;
      }
      this.rebuyBustedPlayers();
      this.dealer = this.nextLiveIndex(this.dealer);
    }
    this.generation += 1;
    this.handNumber += 1;
    this.handOver = false;
    this.showdown = false;
    this.currentActor = null;
    this.deck = makeDeck();
    this.board = [];
    this.street = 0;
    this.raisesThisStreet = 0;
    this.ui.nextHand.hidden = true;
    this.players.forEach((player) => Object.assign(player, {
      hole: [], folded: player.chips <= 0, allIn: false, contribution: 0, streetBet: 0, lastAction: player.chips <= 0 ? "出局" : "",
    }));
    const live = this.livePlayers();
    if (!live.includes(this.players[this.dealer])) this.dealer = this.nextLiveIndex(this.dealer - 1);
    this.setPositions(live);
    for (let round = 0; round < 2; round += 1) {
      live.forEach((player) => player.hole.push(this.deck.pop()));
    }
    this.pay(this.smallBlindPlayer, Math.min(SMALL_BLIND, this.smallBlindPlayer.chips));
    this.pay(this.bigBlindPlayer, Math.min(BIG_BLIND, this.bigBlindPlayer.chips));
    this.smallBlindPlayer.lastAction = `小盲 ${this.smallBlindPlayer.streetBet}`;
    this.bigBlindPlayer.lastAction = `大盲 ${this.bigBlindPlayer.streetBet}`;
    this.log(`第 ${this.handNumber} 手牌 · ${this.players[this.dealer].name} 在庄位`, "system");
    this.log(`${this.smallBlindPlayer.name} 小盲 ${this.smallBlindPlayer.streetBet}`);
    this.log(`${this.bigBlindPlayer.name} 大盲 ${this.bigBlindPlayer.streetBet}`);
    this.render();
    this.startBettingRound(true);
  }

  setPositions(live) {
    const liveIds = new Set(live.map((player) => player.id));
    const findNext = (after) => {
      for (let offset = 1; offset <= this.players.length; offset += 1) {
        const index = (after + offset + this.players.length) % this.players.length;
        if (liveIds.has(index)) return index;
      }
      return after;
    };
    if (live.length === 2) {
      this.smallBlindIndex = this.dealer;
      this.bigBlindIndex = findNext(this.dealer);
    } else {
      this.smallBlindIndex = findNext(this.dealer);
      this.bigBlindIndex = findNext(this.smallBlindIndex);
    }
    this.smallBlindPlayer = this.players[this.smallBlindIndex];
    this.bigBlindPlayer = this.players[this.bigBlindIndex];
  }

  nextLiveIndex(after) {
    for (let offset = 1; offset <= this.players.length; offset += 1) {
      const index = (after + offset + this.players.length) % this.players.length;
      if (this.players[index].chips > 0) return index;
    }
    return 0;
  }

  canRebuy(player) {
    return player.chips <= 0 && player.buyInsUsed < this.maxBuyIns;
  }

  canContinueMatch() {
    const humanAvailable = this.human.chips > 0 || this.canRebuy(this.human);
    const cpuAvailable = this.players.some((player) => !player.human && (player.chips > 0 || this.canRebuy(player)));
    return humanAvailable && cpuAvailable;
  }

  rebuyBustedPlayers() {
    this.players.forEach((player) => {
      if (!this.canRebuy(player)) return;
      player.chips = this.startingChips;
      player.buyInsUsed += 1;
      this.log(`${player.name} 重新买入 ${this.startingChips}（${player.buyInsUsed}/${this.maxBuyIns}）`, player.human ? "human" : "system");
    });
  }

  orderedAfter(index) {
    return [...this.players.slice(index + 1), ...this.players.slice(0, index + 1)];
  }

  livePlayers() { return this.players.filter((player) => player.chips > 0); }
  activePlayers() { return this.players.filter((player) => player.hole.length && !player.folded); }
  pot() { return this.players.reduce((sum, player) => sum + player.contribution, 0); }

  pay(player, amount) {
    const paid = Math.min(Math.max(0, amount), player.chips);
    player.chips -= paid;
    player.contribution += paid;
    player.streetBet += paid;
    if (player.chips === 0) player.allIn = true;
    return paid;
  }

  startBettingRound(preflop = false) {
    this.raisesThisStreet = 0;
    const after = preflop ? this.bigBlindIndex : this.dealer;
    this.actionOrder = this.orderedAfter(after).filter((player) => !player.folded && !player.allIn);
    this.queue = this.actionOrder.slice();
    this.currentBet = Math.max(0, ...this.activePlayers().map((player) => player.streetBet));
    this.minRaise = BIG_BLIND;
    this.processNext();
  }

  processNext() {
    if (this.handOver) return;
    if (this.activePlayers().length === 1) {
      this.awardUncontested();
      return;
    }
    while (this.queue.length && (this.queue[0].folded || this.queue[0].allIn)) this.queue.shift();
    if (!this.queue.length) {
      this.finishBettingRound();
      return;
    }
    const player = this.queue.shift();
    this.currentActor = player;
    const toCall = Math.max(0, this.currentBet - player.streetBet);
    this.render();
    if (player.human) {
      this.awaitHuman(player, toCall);
      return;
    }
    const generation = this.generation;
    window.setTimeout(() => {
      if (generation !== this.generation || this.handOver) return;
      const decision = this.cpuDecision(player, toCall);
      this.applyAction(player, decision.action, decision.target || 0);
    }, 420 + Math.random() * 380);
  }

  awaitHuman(player, toCall) {
    this.pendingHuman = { player, toCall };
    this.ui.fold.disabled = toCall === 0;
    this.ui.checkCall.disabled = false;
    this.ui.checkCall.textContent = toCall ? `跟注 ${Math.min(toCall, player.chips)}` : "过牌";
    this.ui.allIn.disabled = player.chips === 0;
    const maxTarget = player.streetBet + player.chips;
    const minTarget = this.currentBet === 0 ? BIG_BLIND : this.currentBet + this.minRaise;
    const canRaise = maxTarget >= minTarget;
    this.ui.betRaise.disabled = !canRaise;
    this.ui.betRaise.textContent = this.currentBet ? "加注" : "下注";
    this.ui.sizing.style.opacity = canRaise ? "1" : ".38";
    [...this.ui.sizing.querySelectorAll("input, button")].forEach((element) => { element.disabled = !canRaise; });
    const suggested = this.currentBet === 0
      ? roundToBlind(this.pot() * 0.66)
      : this.currentBet + Math.max(this.minRaise, roundToBlind(this.pot() * 0.55));
    const value = clamp(suggested, Math.min(minTarget, maxTarget), maxTarget);
    this.ui.slider.min = Math.min(minTarget, maxTarget);
    this.ui.slider.max = maxTarget;
    this.ui.slider.step = 10;
    this.ui.slider.value = value;
    this.ui.amount.min = Math.min(minTarget, maxTarget);
    this.ui.amount.max = maxTarget;
    this.ui.amount.value = value;
    this.ui.decision.textContent = toCall ? `需要跟注 ${Math.min(toCall, player.chips)}` : "可以过牌或主动下注";
    this.ui.odds.textContent = toCall ? `底池赔率 ${(toCall / (this.pot() + toCall) * 100).toFixed(0)}%` : `最小下注 ${BIG_BLIND}`;
  }

  disableControls(message = "等待其他玩家行动") {
    [this.ui.fold, this.ui.checkCall, this.ui.betRaise, this.ui.allIn].forEach((button) => { button.disabled = true; });
    [...this.ui.sizing.querySelectorAll("input, button")].forEach((element) => { element.disabled = true; });
    this.ui.sizing.style.opacity = ".38";
    this.ui.decision.textContent = message;
    this.ui.odds.textContent = "";
    this.pendingHuman = null;
  }

  submitHuman(action, target = 0) {
    if (!this.pendingHuman) return;
    const { player, toCall } = this.pendingHuman;
    if (action === "raise") {
      const maxTarget = player.streetBet + player.chips;
      const minTarget = this.currentBet === 0 ? BIG_BLIND : this.currentBet + this.minRaise;
      const requestedAllIn = Number(target) === maxTarget;
      target = requestedAllIn ? maxTarget : Math.floor(Number(target) / 10) * 10;
      if (target < minTarget && target !== maxTarget) {
        this.ui.decision.textContent = `最小目标注额为 ${minTarget}`;
        return;
      }
      if (target > maxTarget || !Number.isFinite(target)) {
        this.ui.decision.textContent = `最大目标注额为 ${maxTarget}`;
        return;
      }
    }
    if (action === "fold" && toCall === 0) return;
    this.disableControls();
    this.applyAction(player, action, target);
  }

  setQuickSize(fraction) {
    if (!this.pendingHuman) return;
    const player = this.pendingHuman.player;
    const maxTarget = player.streetBet + player.chips;
    const minTarget = this.currentBet === 0 ? BIG_BLIND : this.currentBet + this.minRaise;
    const target = this.currentBet === 0
      ? roundToBlind(this.pot() * fraction)
      : this.currentBet + Math.max(this.minRaise, roundToBlind(this.pot() * fraction));
    const value = clamp(target, Math.min(minTarget, maxTarget), maxTarget);
    this.ui.slider.value = value;
    this.ui.amount.value = value;
  }

  applyAction(player, action, target = 0) {
    const toCall = Math.max(0, this.currentBet - player.streetBet);
    if (action === "fold") {
      player.folded = true;
      player.lastAction = "弃牌";
      this.log(`${player.name} 弃牌`, player.human ? "human fold" : "fold");
    } else if (action === "call") {
      const paid = this.pay(player, toCall);
      player.lastAction = paid === 0 ? "过牌" : `跟注 ${paid}${player.allIn ? " · 全下" : ""}`;
      this.log(`${player.name} ${player.lastAction}`, player.human ? "human" : "");
    } else if (action === "raise") {
      const oldBet = this.currentBet;
      target = Math.min(target, player.streetBet + player.chips);
      this.pay(player, target - player.streetBet);
      const newBet = player.streetBet;
      const raiseSize = newBet - oldBet;
      const verb = oldBet === 0 ? "下注到" : newBet > oldBet ? "加注到" : "跟注到";
      player.lastAction = `${verb} ${newBet}${player.allIn ? " · 全下" : ""}`;
      this.log(`${player.name} ${player.lastAction}`, player.human ? "human" : "");
      if (newBet > oldBet) {
        if (raiseSize >= this.minRaise) this.minRaise = raiseSize;
        this.currentBet = newBet;
        this.raisesThisStreet += 1;
        const position = this.actionOrder.indexOf(player);
        this.queue = [...this.actionOrder.slice(position + 1), ...this.actionOrder.slice(0, position)]
          .filter((other) => other !== player && !other.folded && !other.allIn);
      }
    }
    this.currentActor = null;
    this.render();
    this.processNext();
  }

  cpuDecision(player, toCall) {
    const { strength, draw } = this.cpuStrength(player);
    const opponents = Math.max(1, this.activePlayers().length - 1);
    const valueThreshold = 0.71 + (opponents - 1) * 0.025 - player.aggression * 0.08;
    const bluffCandidate = strength < 0.32 || (strength < 0.49 && draw > 0);
    const bluff = bluffCandidate && Math.random() < player.bluffRate + draw * 0.25;
    const valueRaise = strength >= valueThreshold && Math.random() < 0.65 + player.aggression * 0.25;
    if ((valueRaise || bluff) && player.chips > toCall && this.raisesThisStreet < 4) {
      return { action: "raise", target: this.cpuRaiseTarget(player, strength, bluff) };
    }
    if (toCall === 0) return { action: "call" };
    const potOdds = toCall / (this.pot() + toCall);
    const pressure = Math.min(0.18, toCall / Math.max(1, player.chips + toCall) * 0.22);
    const required = Math.max(0.20, potOdds + pressure - draw - player.aggression * 0.04);
    const bluffCatch = Math.random() < 0.025 + player.aggression * 0.06;
    return strength >= required || draw >= 0.1 || bluffCatch ? { action: "call" } : { action: "fold" };
  }

  cpuRaiseTarget(player, strength, bluff) {
    const fraction = bluff ? 0.55 + Math.random() * 0.35 : strength > 0.82 ? 0.68 + Math.random() * 0.32 : 0.48 + Math.random() * 0.28;
    const sized = roundToBlind(this.pot() * fraction);
    const target = this.currentBet === 0 ? sized : this.currentBet + Math.max(this.minRaise, sized);
    return Math.min(target, player.streetBet + player.chips);
  }

  cpuStrength(player) {
    const cards = [...player.hole, ...this.board];
    const draw = this.drawBonus(cards);
    if (cards.length >= 5) {
      const category = evaluate(cards)[0];
      const values = [0.14, 0.39, 0.57, 0.68, 0.76, 0.82, 0.9, 0.97, 1];
      return { strength: values[category], draw };
    }
    const [high, low] = player.hole.map((card) => card.rank).sort((a, b) => b - a);
    if (high === low) return { strength: Math.min(0.9, 0.43 + high / 32), draw: 0 };
    const suited = player.hole[0].suit === player.hole[1].suit;
    const connected = Math.abs(high - low) <= 2;
    return { strength: Math.min(0.7, 0.1 + high / 28 + (suited ? 0.07 : 0) + (connected ? 0.06 : 0)), draw: 0 };
  }

  handLabel(player) {
    if (!player.hole?.length) return "";
    const cards = [...player.hole, ...this.board];
    if (cards.length >= 5) return HAND_NAMES[evaluate(cards)[0]];
    const [first, second] = player.hole;
    if (first.rank === second.rank) return "口袋对子";
    if (first.suit === second.suit) return "同花起手牌";
    if (Math.abs(first.rank - second.rank) <= 2) return "连张起手牌";
    return "高牌起手牌";
  }

  drawBonus(cards) {
    const suitCounts = {};
    cards.forEach((card) => { suitCounts[card.suit] = (suitCounts[card.suit] || 0) + 1; });
    const ranks = new Set(cards.map((card) => card.rank));
    if (ranks.has(14)) ranks.add(1);
    const flushDraw = Object.values(suitCounts).some((count) => count === 4);
    let straightDraw = false;
    for (let start = 1; start <= 10; start += 1) {
      let found = 0;
      for (let rank = start; rank < start + 5; rank += 1) if (ranks.has(rank)) found += 1;
      if (found === 4) straightDraw = true;
    }
    return (flushDraw ? 0.13 : 0) + (straightDraw ? 0.1 : 0);
  }

  finishBettingRound() {
    this.currentActor = null;
    this.disableControls("本轮行动结束");
    if (this.activePlayers().length === 1) {
      this.awardUncontested();
      return;
    }
    if (this.street === 3) {
      this.showdownHand();
      return;
    }
    const generation = this.generation;
    window.setTimeout(() => {
      if (generation !== this.generation || this.handOver) return;
      this.advanceStreet();
    }, 550);
  }

  advanceStreet() {
    this.street += 1;
    this.players.forEach((player) => { player.streetBet = 0; player.lastAction = player.folded ? "弃牌" : player.allIn ? "全下" : ""; });
    this.deck.pop();
    const count = this.street === 1 ? 3 : 1;
    for (let i = 0; i < count; i += 1) this.board.push(this.deck.pop());
    this.log(`${STREET_NAMES[this.street]} · ${this.board.map(cardText).join(" ")}`, "system");
    this.render();
    const canAct = this.activePlayers().filter((player) => !player.allIn);
    if (canAct.length <= 1) {
      if (this.street === 3) this.showdownHand();
      else window.setTimeout(() => this.advanceStreet(), 650);
      return;
    }
    this.startBettingRound(false);
  }

  awardUncontested() {
    const winner = this.activePlayers()[0];
    const amount = this.pot();
    winner.chips += amount;
    this.players.forEach((player) => { player.contribution = 0; });
    this.log(`${winner.name} 赢得无人争夺的底池 ${amount}`, winner.human ? "human" : "system");
    this.endHand(`${winner.name} 赢得 ${amount}`);
  }

  showdownHand() {
    this.showdown = true;
    const active = this.activePlayers();
    const scores = new Map(active.map((player) => [player.id, evaluate([...player.hole, ...this.board])]));
    active.forEach((player) => this.log(`${player.name}：${cardText(player.hole[0])} ${cardText(player.hole[1])} · ${HAND_NAMES[scores.get(player.id)[0]]}`));
    const levels = [...new Set(this.players.map((player) => player.contribution).filter(Boolean))].sort((a, b) => a - b);
    let previous = 0;
    levels.forEach((level, index) => {
      const contributors = this.players.filter((player) => player.contribution >= level);
      const eligible = contributors.filter((player) => !player.folded);
      const amount = (level - previous) * contributors.length;
      previous = level;
      if (!eligible.length || amount <= 0) return;
      const best = eligible.map((player) => scores.get(player.id)).sort((a, b) => compareScores(b, a))[0];
      const winners = eligible.filter((player) => compareScores(scores.get(player.id), best) === 0);
      const share = Math.floor(amount / winners.length);
      let remainder = amount % winners.length;
      winners.forEach((winner) => { winner.chips += share + (remainder-- > 0 ? 1 : 0); });
      const label = index === 0 ? "主池" : `边池 ${index}`;
      this.log(`${winners.map((winner) => winner.name).join("、")} 赢得${label} ${amount}`, winners.some((winner) => winner.human) ? "human" : "system");
    });
    this.players.forEach((player) => { player.contribution = 0; });
    this.render();
    this.endHand("摊牌结束");
  }

  endHand(message) {
    this.handOver = true;
    this.currentActor = null;
    this.disableControls(message);
    this.ui.message.textContent = message;
    this.ui.nextHand.hidden = false;
    if (this.human.chips <= 0 && !this.canRebuy(this.human)) {
      this.ui.nextHand.textContent = "重新开始";
      this.ui.message.textContent = "你的买入次数已用完";
    } else if (!this.players.some((player) => !player.human && (player.chips > 0 || this.canRebuy(player)))) {
      this.ui.nextHand.textContent = "重新开始";
      this.ui.message.textContent = "所有 CPU 的买入次数均已用完";
    } else {
      this.ui.nextHand.textContent = "下一手";
      if (this.human.chips <= 0) this.ui.message.textContent = "下一手将为你自动重新买入";
    }
    this.render();
  }

  render() {
    this.ui.street.textContent = STREET_NAMES[this.street] || "结束";
    this.ui.handNumber.textContent = `#${this.handNumber}`;
    this.ui.pot.textContent = this.pot();
    this.ui.board.innerHTML = "";
    this.board.forEach((card) => this.ui.board.append(this.cardElement(card)));
    for (let i = this.board.length; i < 5; i += 1) {
      const placeholder = document.createElement("div");
      placeholder.className = "card-placeholder";
      this.ui.board.append(placeholder);
    }
    this.renderSeats();
    if (!this.handOver) this.ui.message.textContent = this.currentActor ? `${this.currentActor.name} 思考中` : STREET_NAMES[this.street];
  }

  renderSeats() {
    const cpuPositions = {
      1: [3], 2: [2, 4], 3: [1, 3, 5], 4: [1, 2, 4, 5], 5: [1, 2, 3, 4, 5],
    }[this.players.length - 1];
    this.ui.seats.innerHTML = "";
    this.players.forEach((player, index) => {
      const seat = document.createElement("article");
      const position = player.human ? 0 : cpuPositions[index - 1];
      seat.className = `seat pos-${position}${player.folded ? " folded" : ""}${this.currentActor === player ? " active" : ""}`;
      const badges = [];
      if (index === this.dealer) badges.push("<span class=\"badge\">D</span>");
      if (index === this.smallBlindIndex) badges.push("<span class=\"badge blind\">SB</span>");
      if (index === this.bigBlindIndex) badges.push("<span class=\"badge blind\">BB</span>");
      seat.innerHTML = `
        <div class="badges">${badges.join("")}</div>
        <div class="seat-name"><strong>${player.name}</strong><span class="chips">${player.chips}</span></div>
        <div class="seat-cards"></div>
        <div class="seat-meta"></div>`;
      const cards = seat.querySelector(".seat-cards");
      if (player.hole?.length) {
        player.hole.forEach((card) => cards.append(this.cardElement(card, true, !player.human && !this.showdown)));
      }
      const buyInText = `买入 ${player.buyInsUsed}/${this.maxBuyIns}`;
      const status = player.chips <= 0 && this.canRebuy(player) ? "等待重新买入" : player.chips <= 0 ? "出局" : player.lastAction;
      const hand = player.human && player.hole?.length ? this.handLabel(player) : "";
      seat.querySelector(".seat-meta").textContent = [hand, status, buyInText].filter(Boolean).join(" · ");
      this.ui.seats.append(seat);
    });
  }

  cardElement(card, small = false, hidden = false) {
    const element = document.createElement("div");
    element.className = `card${small ? " small" : ""}${hidden ? " back" : ""}${!hidden && ["h", "d"].includes(card.suit) ? " red" : ""}`;
    if (hidden) {
      element.textContent = "◆";
    } else {
      element.innerHTML = `<span>${RANKS[card.rank] || card.rank}</span><span class="suit">${SUITS[card.suit]}</span>`;
    }
    return element;
  }

  log(message, className = "") {
    const item = document.createElement("li");
    item.className = className;
    item.innerHTML = `<time>${STREET_NAMES[this.street] || "牌局"}</time><span>${message}</span>`;
    this.ui.log.append(item);
    this.ui.log.scrollTop = this.ui.log.scrollHeight;
  }
}

window.addEventListener("DOMContentLoaded", () => { window.pokerGame = new PokerGame(); });
