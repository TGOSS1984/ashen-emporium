import pytest
from django.urls import NoReverseMatch, reverse

from catalog.models import Product

pytestmark = pytest.mark.django_db


def make_product(**overrides) -> Product:
    """
    Create an active Product suitable for cart tests.

    Cart relies on:
    - Product.price_pence for pricing
    - Product.is_active=True to be returned in Cart.items()
    """
    data = {
        "name": "Test Product",
        "sku": "SKU-TEST-1",
        "category": "armour",
        "slug": "test-product",
        "price_pence": 10000,  # £100.00
        "is_active": True,
        **overrides,
    }
    return Product.objects.create(**data)


def _reverse_first(name_candidates, *args):
    """
    Return the first reverse() that exists from a list of candidates.
    Helps avoid brittle tests if URL names change.
    """
    for name in name_candidates:
        try:
            return reverse(name, args=args)
        except NoReverseMatch:
            continue
    raise NoReverseMatch(
        f"No matching URL name found. Tried: {', '.join(name_candidates)}"
    )


def test_cart_add_item(client):
    p = make_product(name="Ashen Helm", sku="SKU-HELM-1", slug="ashen-helm")

    url = reverse("cart_add", args=[p.id])
    res = client.post(url, data={"qty": 1}, follow=True)

    assert res.status_code == 200
    cart = client.session.get("cart", {})
    assert str(p.id) in cart
    assert cart[str(p.id)]["qty"] == 1


def test_cart_update_quantity(client):
    p = make_product(name="Ashen Greaves", sku="SKU-GREAVES-1", slug="ashen-greaves")

    # Add one first
    client.post(reverse("cart_add", args=[p.id]), data={"qty": 1})

    # Try common URL names for "set/update quantity"
    update_url = _reverse_first(
        [
            "cart_set_qty",
            "cart_update",
            "cart_update_item",
            "cart_set_quantity",
            "cart_update_quantity",
            "cart_set",
        ],
        p.id,
    )

    client.post(update_url, data={"qty": 3})

    cart = client.session.get("cart", {})
    assert cart[str(p.id)]["qty"] == 3


def test_cart_remove_item(client):
    p = make_product(name="Ashen Gauntlets", sku="SKU-GAUNT-1", slug="ashen-gauntlets")

    client.post(reverse("cart_add", args=[p.id]), data={"qty": 1})

    url = reverse("cart_remove", args=[p.id])
    client.post(url)

    cart = client.session.get("cart", {})
    assert str(p.id) not in cart

