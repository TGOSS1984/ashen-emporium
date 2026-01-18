from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product
from .cart import Cart


def cart_detail(request):
    cart = Cart(request.session)
    items = list(cart.items())
    total_pence = cart.total_pence()
    total_gbp = f"£{total_pence/100:,.2f}"

    return render(
        request,
        "cart/cart_detail.html",
        {"items": items, "total_gbp": total_gbp},
    )


@require_POST
def cart_add(request, product_id: int):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    qty_raw = request.POST.get("qty", "1")
    try:
        qty = int(qty_raw)
    except ValueError:
        qty = 1

    if qty < 1:
        qty = 1

    cart = Cart(request.session)
    cart.add(product_id=product.id, qty=qty)
    messages.success(request, f"Added {product.name} to your basket.")
    return redirect(product.get_absolute_url())


@require_POST
def cart_update(request, product_id: int):
    qty_raw = request.POST.get("qty", "1")
    try:
        qty = int(qty_raw)
    except ValueError:
        qty = 1

    cart = Cart(request.session)
    cart.set_qty(product_id=product_id, qty=qty)
    messages.info(request, "Basket updated.")
    return redirect("cart_detail")


@require_POST
def cart_remove(request, product_id: int):
    cart = Cart(request.session)
    cart.remove(product_id=product_id)
    messages.info(request, "Item removed from basket.")
    return redirect("cart_detail")
