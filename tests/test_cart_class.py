import pytest

from catalog.models import Product
from cart.cart import Cart, CART_SESSION_KEY

pytestmark = pytest.mark.django_db


class DummySession(dict):
    """Minimal session-like object: dict + `.modified` flag."""
    modified: bool = False


def make_product(**overrides) -> Product:
    """
    Create an active Product suitable for cart class tests.

    Cart relies on:
    - Product.price_pence for pricing
    - Product.is_active=True to be returned in Cart.items()
    """
    data = {
        "name": "Test Product",
        "sku": "SKU-TEST-1",
        "category": "misc",
        "slug": "test-product",
        "price_pence": 10000,  # £100.00
        "is_active": True,
        **overrides,
    }
    return Product.objects.create(**data)


def test_cart_count_items_and_clear():
    session = DummySession()
    cart = Cart(session)

    p = make_product(
        name="Cinder Blade",
        sku="SKU-WEP-1",
        category="weapon",
        slug="cinder-blade",
        price_pence=20000,  # £200.00
    )

    cart.add(product_id=p.id, qty=2)

    assert cart.count_items() == 2
    assert session.modified is True

    cart.clear()
    assert session.get(CART_SESSION_KEY, {}) == {}
    assert session.modified is True


def test_cart_items_and_total_pence():
    session = DummySession()
    cart = Cart(session)

    p1 = make_product(
        name="Ember Charm",
        sku="SKU-EMB-1",
        slug="ember-charm",
        price_pence=5000,   # £50.00
    )
    p2 = make_product(
        name="Ash Ring",
        sku="SKU-RNG-1",
        slug="ash-ring",
        price_pence=7500,   # £75.00
    )

    cart.add(product_id=p1.id, qty=1)
    cart.add(product_id=p2.id, qty=2)

    items = list(cart.items())
    assert len(items) == 2

    assert cart.total_pence() == 5000 + (7500 * 2)
    assert session.modified is True


