from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from cart.cart import Cart
from .models import Order, OrderItem


@login_required
def checkout(request):
    cart = Cart(request.session)
    items = list(cart.items())

    if not items:
        messages.info(request, "Your basket is empty.")
        return redirect("product_list")

    total_pence = cart.total_pence()

    if request.method == "POST":
        # ✅ Stock check BEFORE creating the order
        for item in items:
            if item.product.stock_qty < item.qty:
                messages.error(
                    request,
                    f"Not enough stock for {item.product.name}. Please adjust your basket."
                )
                return redirect("cart_detail")

        order = Order.objects.create(
            user=request.user,
            email=request.user.email or "",
            total_pence=total_pence,
            status=Order.Status.PLACED,
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product_name=item.product.name,
                sku=item.product.sku,
                unit_price_pence=item.product.price_pence,
                qty=item.qty,
                line_total_pence=item.line_total_pence,
            )

        cart.clear()
        messages.success(request, "Order placed successfully.")
        return redirect("order_confirmation", order_id=order.id)

    total_gbp = f"£{total_pence/100:,.2f}"

    return render(
        request,
        "orders/checkout.html",
        {"items": items, "total_gbp": total_gbp},
    )



@login_required
def order_confirmation(request, order_id: int):
    order = Order.objects.prefetch_related("items").get(id=order_id, user=request.user)
    return render(request, "orders/order_confirmation.html", {"order": order})
