"""
Per-card behavioural history — the signal real fraud systems rely on most.

A single transaction says little; the same transaction as "the 6th on this
card in 20 minutes, 9x the card's usual amount, first time in this country"
says a lot. The store keeps a short rolling history per card and turns it
into features.

The SAME store class is used for training (replaying historical
transactions in time order) and for live scoring, so the model never sees
features at serving time that were computed differently during training.

Backends:
  MemoryHistoryStore  - single process (desktop app, tests, one API worker)
  RedisHistoryStore   - shared by several API workers / the Kafka consumer
"""
import math
import threading
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Set, Tuple

HISTORY_FEATURES: List[str] = [
    "card_txn_count_1h",
    "card_txn_count_24h",
    "card_amount_24h_log",
    "secs_since_last_txn_log",
    "amount_to_card_mean",
    "is_new_country",
    "is_new_category",
    "is_new_device",
    "card_history_len_log",
]

MAX_EVENTS = 500         # per card, enough for a 24h window on busy cards
MEAN_WINDOW = 50         # amounts used for the card's "usual" amount
NO_HISTORY_GAP = 30 * 24 * 3600  # treat "never seen" as a 30-day gap


def compute_history_features(
    events: List[Tuple[float, float]],
    countries: Set[str],
    categories: Set[str],
    devices: Set[str],
    history_len: int,
    ts: float,
    amount: float,
    country: str,
    category: str,
    device: str,
) -> Dict[str, float]:
    """
    events: previous (timestamp, amount) pairs for this card, any order.
    Only PRIOR activity is used; the transaction being scored is not in it.
    """
    count_1h = count_24h = 0
    amount_24h = 0.0
    last_ts = None
    for e_ts, e_amt in events:
        if last_ts is None or e_ts > last_ts:
            last_ts = e_ts
        age = ts - e_ts
        if 0 <= age <= 86400:
            count_24h += 1
            amount_24h += e_amt
            if age <= 3600:
                count_1h += 1

    recent = sorted(events, key=lambda e: e[0], reverse=True)[:MEAN_WINDOW]
    mean_amount = (sum(a for _, a in recent) / len(recent)) if recent else None
    gap = max(ts - last_ts, 0.0) if last_ts is not None else NO_HISTORY_GAP
    has_history = history_len > 0

    return {
        "card_txn_count_1h": float(count_1h),
        "card_txn_count_24h": float(count_24h),
        "card_amount_24h_log": math.log1p(amount_24h),
        "secs_since_last_txn_log": math.log1p(gap),
        "amount_to_card_mean": (amount / (mean_amount + 1.0)) if mean_amount is not None else 1.0,
        "is_new_country": float(has_history and country not in countries),
        "is_new_category": float(has_history and category not in categories),
        "is_new_device": float(has_history and device not in devices),
        "card_history_len_log": math.log1p(history_len),
    }


def empty_history_features() -> Dict[str, float]:
    """Features for a transaction with no card id (no history possible)."""
    return compute_history_features([], set(), set(), set(), 0, 0.0, 0.0, "", "", "")


@dataclass
class _CardState:
    events: Deque[Tuple[float, float]] = field(default_factory=lambda: deque(maxlen=MAX_EVENTS))
    countries: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)
    devices: Set[str] = field(default_factory=set)
    count: int = 0


class MemoryHistoryStore:
    """Thread-safe in-process store with an LRU cap on the number of cards."""

    def __init__(self, max_cards: int = 200_000):
        self._cards: "OrderedDict[str, _CardState]" = OrderedDict()
        self._lock = threading.Lock()
        self.max_cards = max_cards

    def _get(self, card_id: str) -> _CardState:
        state = self._cards.get(card_id)
        if state is None:
            state = _CardState()
            self._cards[card_id] = state
            if len(self._cards) > self.max_cards:
                self._cards.popitem(last=False)
        else:
            self._cards.move_to_end(card_id)
        return state

    def score_and_update(self, card_id: Optional[str], ts: float, amount: float,
                         country: str, category: str, device: str) -> Dict[str, float]:
        """Features from history BEFORE this transaction, then record it."""
        if not card_id:
            return empty_history_features()
        with self._lock:
            s = self._get(card_id)
            feats = compute_history_features(
                list(s.events), s.countries, s.categories, s.devices, s.count,
                ts, amount, country, category, device,
            )
            s.events.append((ts, amount))
            s.countries.add(country)
            s.categories.add(category)
            s.devices.add(device)
            s.count += 1
        return feats

    def peek(self, card_id: Optional[str], ts: float, amount: float,
             country: str, category: str, device: str) -> Dict[str, float]:
        """Features without recording the transaction (what-if scoring)."""
        if not card_id:
            return empty_history_features()
        with self._lock:
            s = self._cards.get(card_id)
            if s is None:
                return compute_history_features([], set(), set(), set(), 0, ts, amount, country, category, device)
            return compute_history_features(
                list(s.events), s.countries, s.categories, s.devices, s.count,
                ts, amount, country, category, device,
            )

    def clear(self):
        with self._lock:
            self._cards.clear()

    def __len__(self):
        return len(self._cards)


class RedisHistoryStore:
    """Same behaviour as MemoryHistoryStore, shared through Redis."""

    def __init__(self, url: str = "redis://localhost:6379/0", prefix: str = "fraud:card:", client=None):
        if client is None:
            import redis  # optional dependency
            client = redis.Redis.from_url(url, decode_responses=True)
        self.r = client
        self.prefix = prefix

    def _keys(self, card_id: str):
        base = f"{self.prefix}{card_id}"
        return base + ":events", base + ":countries", base + ":categories", base + ":devices", base + ":count"

    def _read(self, card_id: str):
        ev_k, co_k, ca_k, de_k, cnt_k = self._keys(card_id)
        pipe = self.r.pipeline()
        pipe.lrange(ev_k, 0, MAX_EVENTS - 1)
        pipe.smembers(co_k)
        pipe.smembers(ca_k)
        pipe.smembers(de_k)
        pipe.get(cnt_k)
        raw, countries, categories, devices, count = pipe.execute()
        events = []
        for item in raw:
            t, a = item.split("|", 1)
            events.append((float(t), float(a)))
        return events, set(countries), set(categories), set(devices), int(count or 0)

    def peek(self, card_id, ts, amount, country, category, device):
        if not card_id:
            return empty_history_features()
        events, countries, categories, devices, count = self._read(card_id)
        return compute_history_features(events, countries, categories, devices, count,
                                        ts, amount, country, category, device)

    def score_and_update(self, card_id, ts, amount, country, category, device):
        if not card_id:
            return empty_history_features()
        feats = self.peek(card_id, ts, amount, country, category, device)
        ev_k, co_k, ca_k, de_k, cnt_k = self._keys(card_id)
        pipe = self.r.pipeline()
        pipe.lpush(ev_k, f"{ts}|{amount}")
        pipe.ltrim(ev_k, 0, MAX_EVENTS - 1)
        pipe.sadd(co_k, country)
        pipe.sadd(ca_k, category)
        pipe.sadd(de_k, device)
        pipe.incr(cnt_k)
        for k in (ev_k, co_k, ca_k, de_k, cnt_k):
            pipe.expire(k, 90 * 24 * 3600)  # forget cards idle for 90 days
        pipe.execute()
        return feats

    def clear(self):
        for key in self.r.scan_iter(f"{self.prefix}*"):
            self.r.delete(key)


def create_history_store(settings: dict):
    """Build the store configured in settings.yaml / env (HISTORY_BACKEND)."""
    cfg = settings.get("history", {}) if settings else {}
    if cfg.get("backend", "memory") == "redis":
        return RedisHistoryStore(cfg.get("redis_url", "redis://localhost:6379/0"))
    return MemoryHistoryStore()
