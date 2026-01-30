import json
from unittest.mock import patch

import pytest
from django.urls import reverse

from orders.models import Order, OrderItem
from catalog.models import Product


@pytest.mark.django_db
def test_webhook_marks_paid_and_decrements_stock(client):
    # Create product with stock
    p = Product.objects.create(
        sku="MENU_KNOWLEDGE_99999",
        name="Webhook Test Armour",
        category=Product.Category.ARMOUR,
        rarity=Product.Rarity.COMMON,
        subtype=Product.Subtype.PLATE,
        price_pence=1299,
        stock_qty=5,
        is_active=True,
    )

    # Create placed order + snapshot item
    order = Order.objects.create(
        email="test@example.com",
        status=Order.Status.PLACED,
        total_pence=1299,
    )
    OrderItem.objects.create(
        order=order,
        product_name=p.name,
        sku=p.sku,
        unit_price_pence=p.price_pence,
        qty=2,
        line_total_pence=p.price_pence * 2,
    )

    url = reverse("stripe_webhook")

    # Fake Stripe event payload (what our code uses)
    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "payment_intent": "pi_test_123",
                "metadata": {"order_id": str(order.id)},
            }
        },
    }

    # Patch Stripe signature verification to return our fake event
    with patch("payments.views.stripe.Webhook.construct_event", return_value=fake_event):
        res = client.post(
            url,
            data=json.dumps(fake_event).encode("utf-8"),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test",
        )

    assert res.status_code == 200

    # Order becomes PAID
    order.refresh_from_db()
    assert order.status == Order.Status.PAID

    # Stock decremented by qty (2)
    p.refresh_from_db()
    assert p.stock_qty == 3

@pytest.mark.django_db
def test_webhook_is_idempotent_does_not_double_decrement(client):
    p = Product.objects.create(
        sku="MENU_KNOWLEDGE_88888",
        name="Idempotency Test",
        category=Product.Category.ARMOUR,
        rarity=Product.Rarity.COMMON,
        subtype=Product.Subtype.PLATE,
        price_pence=1000,
        stock_qty=5,
        is_active=True,
    )

    order = Order.objects.create(
        email="test@example.com",
        status=Order.Status.PLACED,
        total_pence=2000,
    )
    OrderItem.objects.create(
        order=order,
        product_name=p.name,
        sku=p.sku,
        unit_price_pence=p.price_pence,
        qty=2,
        line_total_pence=p.price_pence * 2,
    )

    url = reverse("stripe_webhook")

    fake_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"order_id": str(order.id)}}},
    }

    with patch("payments.views.stripe.Webhook.construct_event", return_value=fake_event):
        # First call
        res1 = client.post(url, data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="test")
        assert res1.status_code == 200

        # Second call (retry)
        res2 = client.post(url, data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="test")
        assert res2.status_code == 200

    p.refresh_from_db()
    assert p.stock_qty == 3  # decremented once only
