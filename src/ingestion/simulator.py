"""
Behavioural transaction simulator.

Each simulated customer has a card, a home country, a usual spend level,
favourite merchant categories, a main device and daily habits. Fraud is
injected the way it happens in practice, as *episodes* on a card:

  account_takeover  - a burst of 3-10 purchases within ~1 hour, far above the
                      customer's usual spend, in risky categories, from another
                      country and/or device
  card_testing      - a few tiny online charges, then one or two large ones
  high_value        - a single unusually large purchase
  stealth           - purchases that match the customer's habits (the share
                      of fraud no model can realistically catch)
  new_card_fraud    - a card never seen before (stolen / synthetic identity)
                      whose first purchases are large, risky and often foreign

Some legitimate customers also join part-way through, so "no history yet"
is not by itself a fraud signal: the model has to look at what a new card
is buying.

Legitimate look-alikes are included on purpose (trips abroad, big
purchases, shopping sprees, micro-payments, late-night shopping) so no single
rule separates fraud from normal behaviour and the reported metrics stay
realistic instead of near-perfect.

`generate_dataset` builds a training set. `LiveSimulator` streams
transactions in real time for the dashboard demo.
"""
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

NORMAL_CATEGORIES = ["grocery", "restaurants", "retail", "fuel", "utilities", "entertainment",
                     "travel", "electronics", "health", "online_shopping"]
RISKY_CATEGORIES = ["electronics", "money_transfer", "cryptocurrency", "gambling", "gift_cards", "travel"]
COUNTRIES = ["US", "UK", "CA", "AU", "DE", "FR", "IN", "SG", "BR", "NG"]
COUNTRY_P = [0.40, 0.10, 0.08, 0.06, 0.07, 0.06, 0.10, 0.05, 0.04, 0.04]
DEVICES = ["mobile", "web", "pos"]


@dataclass
class Customer:
    card_id: str
    home: str
    mean_amount: float
    categories: List[str]
    cat_weights: np.ndarray
    device: str
    daily_rate: float
    peak_hour: float
    trip: Optional[tuple] = None  # (start_day, end_day, country)
    join_day: int = 0             # first day the card is active (new customers)


def _make_customer(i: int, rng: np.random.Generator, days: int) -> Customer:
    cats = list(rng.choice(NORMAL_CATEGORIES, size=4, replace=False))
    if rng.random() < 0.05:            # some customers legitimately gamble
        cats.append("gambling")
    weights = rng.dirichlet(np.ones(len(cats)) * 2)
    home = rng.choice(COUNTRIES, p=COUNTRY_P)
    trip = None
    if rng.random() < 0.06 and days > 10:
        start = int(rng.integers(0, days - 7))
        trip = (start, start + int(rng.integers(3, 8)), str(rng.choice([c for c in COUNTRIES if c != home])))
    return Customer(
        card_id=f"CARD_{i:06d}",
        home=str(home),
        mean_amount=float(np.exp(rng.normal(3.6, 0.6))),
        categories=cats,
        cat_weights=weights,
        device=str(rng.choice(DEVICES, p=[0.55, 0.30, 0.15])),
        daily_rate=float(rng.gamma(2.0, 0.6)),
        peak_hour=float(np.clip(rng.normal(14, 3), 8, 21)),
        trip=trip,  # legit travel abroad (was computed but never attached)
    )


def _normal_txn(c: Customer, when: datetime, rng: np.random.Generator, day: int) -> Dict:
    country = c.home
    if c.trip and c.trip[0] <= day <= c.trip[1]:
        country = c.trip[2]
    category = str(rng.choice(c.categories, p=c.cat_weights))
    device = c.device if rng.random() < 0.85 else str(rng.choice(DEVICES))
    amount = c.mean_amount * float(np.exp(rng.normal(0, 0.6)))
    r = rng.random()
    if r < 0.04:                                        # legit big purchase (TV, flights, rent...)
        amount *= float(rng.uniform(3, 15))
        category = str(rng.choice(["electronics", "travel", "retail", category]))
    elif r < 0.07:                                      # legit micro-payments (apps, parking)
        amount = float(rng.uniform(0.5, 5))
        category, device = "online_shopping", "web"
    elif r < 0.075:                                     # legit purchase in a "risky" category
        category = str(rng.choice(RISKY_CATEGORIES))
    if rng.random() < 0.004:                            # legit cross-border online purchase
        country = str(rng.choice(COUNTRIES))
    return {
        "card_id": c.card_id,
        "timestamp": when,
        "amount": round(max(amount, 0.5), 2),
        "merchant_category": category,
        "device_type": device,
        "location_country": country,
        "is_fraud": 0,
        "scenario": "normal",
    }


def _shopping_spree(c: Customer, start: datetime, rng: np.random.Generator, day: int) -> List[Dict]:
    """Legit burst: several purchases within an hour (looks like takeover velocity)."""
    out, t = [], start
    for _ in range(int(rng.integers(3, 7))):
        tx = _normal_txn(c, t, rng, day)
        tx["amount"] = round(tx["amount"] * float(rng.uniform(1, 4)), 2)
        out.append(tx)
        t += timedelta(minutes=float(rng.uniform(3, 20)))
    return out


def _txn_time(day_start: datetime, c: Customer, rng: np.random.Generator) -> datetime:
    if rng.random() < 0.04:                             # legit late-night activity
        hour = float(rng.uniform(0, 6))
    else:
        hour = float(np.clip(rng.normal(c.peak_hour, 3.5), 6, 23.9))
    return day_start + timedelta(hours=hour)


def fraud_episode(c: Customer, start: datetime, rng: np.random.Generator, kind: Optional[str] = None) -> List[Dict]:
    """Generate one fraud episode on customer c's card starting at `start`."""
    kind = kind or str(rng.choice(["account_takeover", "card_testing", "high_value", "stealth"],
                                  p=[0.5, 0.2, 0.15, 0.15]))
    foreign = str(rng.choice([x for x in COUNTRIES if x != c.home]))
    attacker_device = str(rng.choice([d for d in DEVICES if d != c.device]))
    txns: List[Dict] = []
    t = start

    def add(amount, category, country, device):
        txns.append({
            "card_id": c.card_id, "timestamp": t, "amount": round(max(float(amount), 0.5), 2),
            "merchant_category": category, "device_type": device, "location_country": country,
            "is_fraud": 1, "scenario": kind,
        })

    def category():
        # Fraudsters often blend in with the victim's usual merchants
        return str(rng.choice(RISKY_CATEGORIES)) if rng.random() < 0.6 else str(rng.choice(c.categories, p=c.cat_weights))

    if kind == "account_takeover":
        country = foreign if rng.random() < 0.45 else c.home
        device = attacker_device if rng.random() < 0.5 else c.device
        for _ in range(int(rng.integers(2, 9))):
            add(c.mean_amount * float(np.exp(rng.normal(1.2, 0.8))), category(), country, device)
            t += timedelta(minutes=float(rng.uniform(2, 45)))
    elif kind == "card_testing":
        country = foreign if rng.random() < 0.6 else c.home
        for _ in range(int(rng.integers(2, 5))):
            add(rng.uniform(0.5, 4.0), "online_shopping", country, "web")
            t += timedelta(minutes=float(rng.uniform(0.5, 10)))
        for _ in range(int(rng.integers(1, 3))):
            add(c.mean_amount * float(rng.uniform(2, 20)), category(), country, "web")
            t += timedelta(minutes=float(rng.uniform(1, 30)))
    elif kind == "high_value":
        add(c.mean_amount * float(rng.uniform(5, 25)), category(),
            c.home if rng.random() < 0.6 else foreign, attacker_device if rng.random() < 0.5 else c.device)
    else:  # stealth: looks like the customer's own behaviour; mostly undetectable
        for _ in range(int(rng.integers(1, 3))):
            add(c.mean_amount * float(np.exp(rng.normal(0.4, 0.5))),
                str(rng.choice(c.categories, p=c.cat_weights)), c.home, c.device)
            t += timedelta(hours=float(rng.uniform(1, 12)))
    return txns


def new_card_fraud(card_id: str, start: datetime, rng: np.random.Generator) -> List[Dict]:
    """A brand-new card used by a fraudster: big, risky purchases from the first transaction."""
    country = str(rng.choice(COUNTRIES, p=COUNTRY_P)) if rng.random() < 0.5 else str(rng.choice(COUNTRIES))
    device = "web" if rng.random() < 0.7 else str(rng.choice(DEVICES))
    txns, t = [], start
    for _ in range(int(rng.integers(1, 5))):
        category = str(rng.choice(RISKY_CATEGORIES)) if rng.random() < 0.75 else str(rng.choice(NORMAL_CATEGORIES))
        txns.append({
            "card_id": card_id, "timestamp": t, "amount": round(float(np.exp(rng.normal(5.5, 0.8))), 2),
            "merchant_category": category, "device_type": device, "location_country": country,
            "is_fraud": 1, "scenario": "new_card_fraud",
        })
        t += timedelta(minutes=float(rng.uniform(2, 60)))
    return txns


def generate_dataset(
    n_customers: int = 2000,
    days: int = 60,
    incident_rate: float = 0.15,
    start: str = "2024-01-01",
    seed: int = 42,
) -> pd.DataFrame:
    """
    Simulate `days` of activity for `n_customers` cards.
    incident_rate: expected fraud episodes per customer over the whole period.
    """
    rng = np.random.default_rng(seed)
    base = datetime.fromisoformat(start)
    customers = [_make_customer(i, rng, days) for i in range(n_customers)]
    for c in customers:                             # ~12% of customers open their card mid-period
        if rng.random() < 0.12 and days > 14:
            c.join_day = int(rng.integers(7, days - 5))
    rows: List[Dict] = []

    for c in customers:
        for day in range(c.join_day, days):
            day_start = base + timedelta(days=day)
            for _ in range(int(rng.poisson(c.daily_rate))):
                rows.append(_normal_txn(c, _txn_time(day_start, c, rng), rng, day))
            if rng.random() < 0.015:                    # occasional legit shopping spree
                rows.extend(_shopping_spree(c, _txn_time(day_start, c, rng), rng, day))

    # Episodes start after a warm-up week so most cards have history
    n_incidents = int(rng.poisson(n_customers * incident_rate))
    for _ in range(n_incidents):
        c = customers[int(rng.integers(0, n_customers))]
        day = int(rng.integers(max(min(7, days - 1), c.join_day), days))
        hour = float(rng.uniform(0, 24)) if rng.random() < 0.5 else float(rng.uniform(0, 6))
        rows.extend(fraud_episode(c, base + timedelta(days=day, hours=hour), rng))

    # Fraud on cards with no history at all
    for k in range(int(rng.poisson(n_customers * 0.02))):
        day = int(rng.integers(min(7, days - 1), days))
        when = base + timedelta(days=day, hours=float(rng.uniform(0, 24)))
        rows.extend(new_card_fraud(f"CARD_N{k:06d}", when, rng))

    df = pd.DataFrame(rows).sort_values("timestamp", kind="stable").reset_index(drop=True)
    df.insert(0, "transaction_id", [f"TXN_{i:09d}" for i in range(len(df))])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


class LiveSimulator:
    """
    Transaction stream for the dashboard demo.

    Runs on a SIMULATED clock: each tick advances time the way a pool of
    customers really spreads its purchases over a day. Streaming a pool of
    cards in real seconds would make every card look like a velocity attack
    (dozens of purchases per minute) and flag most legitimate traffic.
    Fraud episodes are injected at `fraud_probability` per tick and their
    burst timing is kept, so takeovers look like takeovers.
    """

    def __init__(self, n_customers: int = 300, fraud_probability: float = 0.03, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self.customers = [_make_customer(900_000 + i, self.rng, 30) for i in range(n_customers)]
        for c in self.customers:
            c.trip = None
        rates = np.array([c.daily_rate for c in self.customers])
        self.customer_p = rates / rates.sum()
        self.mean_gap = 86400.0 / rates.sum()  # seconds between purchases across the pool
        self.fraud_probability = fraud_probability
        self.queue: Deque[Dict] = deque()
        self.clock = datetime.now()
        self.counter = 0

    def warmup_history(self, days: int = 7) -> List[Dict]:
        """Past normal transactions so live cards have realistic history."""
        txns = []
        for c in self.customers:
            for d in range(days, 0, -1):
                day_start = (self.clock - timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
                for _ in range(int(self.rng.poisson(c.daily_rate))):
                    txns.append(_normal_txn(c, _txn_time(day_start, c, self.rng), self.rng, 0))
        txns = [t for t in txns if t["timestamp"] < self.clock]
        txns.sort(key=lambda t: t["timestamp"])
        return txns

    def _advance_clock(self):
        # Fewer purchases at night: accept a tick at night only sometimes
        while True:
            self.clock += timedelta(seconds=float(self.rng.exponential(self.mean_gap)))
            if 6 <= self.clock.hour <= 23 or self.rng.random() < 0.12:
                return

    def next_transaction(self) -> Dict:
        if not self.queue and self.rng.random() < self.fraud_probability:
            if self.rng.random() < 0.15:
                self.queue.extend(new_card_fraud(f"CARD_N{self.counter:06d}", self.clock, self.rng))
            else:
                victim = self.customers[int(self.rng.choice(len(self.customers), p=self.customer_p))]
                self.queue.extend(fraud_episode(victim, self.clock, self.rng))

        if self.queue:
            tx = dict(self.queue.popleft())
            self.clock = max(self.clock, tx["timestamp"])
        else:
            self._advance_clock()
            c = self.customers[int(self.rng.choice(len(self.customers), p=self.customer_p))]
            tx = _normal_txn(c, self.clock, self.rng, 0)

        self.counter += 1
        tx["timestamp"] = tx["timestamp"].astimezone().isoformat()
        tx["transaction_id"] = f"SIM_{int(time.time() * 1000)}_{self.counter}"
        return tx

    @staticmethod
    def split_truth(tx: Dict) -> Tuple[Dict, Dict]:
        """Separate the ground truth from what the model is allowed to see."""
        truth = {"is_fraud": bool(tx.pop("is_fraud", 0)), "scenario": tx.pop("scenario", "normal")}
        return tx, truth
