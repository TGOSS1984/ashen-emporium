from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from catalog.models import Product


CART_SESSION_KEY = "cart"


@dataclass(frozen=True)
class CartItem:
    product: Product
    qty: int

    @property
    def line_total_pence(self) -> int:
        return self.product.price_pence * self.qty

    @property
    def line_total_gbp(self) -> str:
        return f"£{self.line_total_pence/100:,.2f}"




class Cart:
    def __init__(self, session):
        self.session = session
        self._data: Dict[str, Dict[str, int]] = session.get(CART_SESSION_KEY, {})

    def save(self) -> None:
        self.session[CART_SESSION_KEY] = self._data
        self.session.modified = True

    def add(self, product_id: int, qty: int = 1) -> None:
        pid = str(product_id)
        if pid not in self._data:
            self._data[pid] = {"qty": 0}
        self._data[pid]["qty"] += qty

        if self._data[pid]["qty"] <= 0:
            self._data.pop(pid, None)

        self.save()

    def set_qty(self, product_id: int, qty: int) -> None:
        pid = str(product_id)
        if qty <= 0:
            self._data.pop(pid, None)
        else:
            self._data[pid] = {"qty": qty}
        self.save()

    def remove(self, product_id: int) -> None:
        self._data.pop(str(product_id), None)
        self.save()

    def clear(self) -> None:
        self._data = {}
        self.save()

    def count_items(self) -> int:
        return sum(item.get("qty", 0) for item in self._data.values())

    def items(self) -> Iterable[CartItem]:
        # Only allow active products to appear in cart display
        ids = [int(pid) for pid in self._data.keys()]
        products = Product.objects.filter(id__in=ids, is_active=True)
        products_by_id = {p.id: p for p in products}

        for pid_str, info in self._data.items():
            pid = int(pid_str)
            product = products_by_id.get(pid)
            if not product:
                continue
            qty = int(info.get("qty", 0))
            if qty > 0:
                yield CartItem(product=product, qty=qty)

    def total_pence(self) -> int:
        return sum(i.line_total_pence for i in self.items())
