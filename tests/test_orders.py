import pytest
from django.urls import reverse

from orders.models import Order


@pytest.mark.django_db
def test_checkout_creates_order_and_items(client, user, product):
    assert client.login(username="tester", password="pass12345")

    # Add product to cart session directly
    session = client.session
    session["cart"] = {str(product.id): {"qty": 2}}
    session.modified = True
    session.save()

    url = reverse("checkout")
    res = client.post(url, follow=True)

    assert res.status_code == 200

    order = Order.objects.latest("id")
    assert order.user == user
    assert order.status == Order.Status.PLACED
    assert order.total_pence == product.price_pence * 2

    items = list(order.items.all())
    assert len(items) == 1
    assert items[0].sku == product.sku
    assert items[0].qty == 2
    assert items[0].line_total_pence == product.price_pence * 2

