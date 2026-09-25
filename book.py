"""Coinbase L2 replacement-size semantics. No trading actions."""
from decimal import Decimal

class OrderBook:
    def __init__(self):
        self.bids = {}
        self.asks = {}
        self.ready = False

    @staticmethod
    def put(side, price, size):
        p, q = Decimal(price), Decimal(size)
        if not p.is_finite() or not q.is_finite() or p <= 0 or q < 0:
            raise ValueError('invalid price or quantity')
        if q == 0:
            side.pop(p, None)
        else:
            side[p] = q

    def apply(self, message):
        if message['type'] == 'snapshot':
            self.bids, self.asks = {}, {}
            for side, key in [(self.bids, 'bids'), (self.asks, 'asks')]:
                for p, q in message[key]:
                    self.put(side, p, q)
            self.ready = True
        elif message['type'] == 'l2update':
            if not self.ready:
                raise ValueError('update before snapshot')
            for side, p, q in message['changes']:
                if side not in ('buy', 'sell'):
                    raise ValueError('unknown side')
                self.put(self.bids if side == 'buy' else self.asks, p, q)
        else:
            return
        self.best()  # Validate after the complete batch, not individual changes.

    def best(self):
        if not self.ready or not self.bids or not self.asks:
            raise ValueError('book unavailable')
        bid, ask = max(self.bids), min(self.asks)
        if bid >= ask:
            raise ValueError('locked or crossed book')
        return float(bid), float(ask), float(self.bids[bid]), float(self.asks[ask])
