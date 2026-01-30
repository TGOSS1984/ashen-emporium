import pytest
from django.urls import reverse
from catalog.models import Product


@pytest.mark.django_db
def test_add_to_cart_adds_item(client, product):
    add_url = reverse("cart_add", kwargs={"product_id": product.id})
    res = client.post(add_url, {"qty": 1}, follow=True)
    assert res.status_code == 200
    # session cart should contain product.id as a string key
    cart = client.session.get("cart", {})
    assert str(product.id) in cart
    assert cart[str(product.id)]["qty"] == 1


@pytest.mark.django_db
def test_armour_set_add_missing_does_not_duplicate(client, armour_set, armour_piece):
    # Add piece once via cart route
    add_url = reverse("cart_add", kwargs={"product_id": armour_piece.id})
    client.post(add_url, {"qty": 1}, follow=True)

    # Now call "add missing pieces only" for the set
    set_add_url = reverse("armour_set_add_to_cart", kwargs={"slug": armour_set.slug})
    res = client.post(set_add_url, {"mode": "missing"}, follow=True)
    assert res.status_code == 200

    cart = client.session.get("cart", {})
    assert str(armour_piece.id) in cart
    # Should still be qty 1 (no duplication)
    assert cart[str(armour_piece.id)]["qty"] == 1
