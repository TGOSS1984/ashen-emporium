import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from django.db import transaction

from orders.models import Order
from catalog.models import Product



stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def start_checkout(request, order_id: int):
    """
    Create a Stripe Checkout Session for an order (must be PLACED and not already PAID).
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == Order.Status.PAID:
        messages.info(request, "This order is already paid.")
        return redirect("order_confirmation", order_id=order.id)

    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "Stripe is not configured (missing secret key).")
        return redirect("order_confirmation", order_id=order.id)
    
    reset = request.GET.get("reset") == "1"

    # Resume existing Stripe session if one already exists (unless reset requested)
    if order.status == Order.Status.PLACED and order.stripe_session_url and not reset:
        return redirect(order.stripe_session_url)


    success_url = request.build_absolute_uri(
        reverse("payment_success")
    ) + f"?order_id={order.id}"
    cancel_url = request.build_absolute_uri(
        reverse("payment_cancel")
    ) + f"?order_id={order.id}"

    # Build line items from order snapshot
    line_items = []
    for item in order.items.all():
        line_items.append(
            {
                "price_data": {
                    "currency": "gbp",
                    "product_data": {"name": item.product_name},
                    "unit_amount": item.unit_price_pence,
                },
                "quantity": item.qty,
            }
        )

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(order.id),  # useful reconciliation value :contentReference[oaicite:2]{index=2}
        metadata={"order_id": str(order.id)},
    )

    order.stripe_session_id = session.id
    order.stripe_payment_intent_id = session.payment_intent or ""
    order.stripe_session_url = session.url or ""
    order.save(update_fields=["stripe_session_id", "stripe_payment_intent_id", "stripe_session_url"])


    return redirect(session.url)


@login_required
def payment_success(request):
    """
    Customer landed here after paying. Webhook will set PAID (source of truth).
    """
    order_id = request.GET.get("order_id")
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id, user=request.user).first()

    return render(request, "payments/success.html", {"order": order})


@login_required
def payment_cancel(request):
    order_id = request.GET.get("order_id")
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id, user=request.user).first()
    return render(request, "payments/cancel.html", {"order": order})


@csrf_exempt
def stripe_webhook(request):
    """
    Verify Stripe signature and handle checkout.session.completed.
    Stripe recommends fulfilling orders via this event and verifying signatures. :contentReference[oaicite:3]{index=3}
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        return HttpResponseBadRequest("Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError:
        return HttpResponseBadRequest("Invalid signature")

    # Event types: checkout.session.completed indicates session completed :contentReference[oaicite:4]{index=4}
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")

        if order_id:
            order = Order.objects.select_for_update().filter(id=order_id).first()

            if order and order.status != Order.Status.PAID:
                with transaction.atomic():
                    # Mark paid
                    order.status = Order.Status.PAID
                    order.stripe_session_id = session.get("id", order.stripe_session_id)
                    order.stripe_payment_intent_id = session.get("payment_intent", order.stripe_payment_intent_id) or ""
                    order.save(update_fields=["status", "stripe_session_id", "stripe_payment_intent_id"])

                    # Decrement stock using the order snapshot
                    for item in order.items.all():
                        # Find the live product by SKU (because OrderItem doesn't FK Product)
                        product = Product.objects.filter(sku=item.sku).first()
                        if not product:
                            continue
                        product.stock_qty = max(product.stock_qty - item.qty, 0)
                        product.save(update_fields=["stock_qty"])


    return HttpResponse(status=200)
