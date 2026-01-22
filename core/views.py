from django.shortcuts import render
from catalog.models import Product


def home(request):
    featured = (
        Product.objects.filter(is_active=True, stock_qty__gt=0)
        .order_by("-rarity", "name")[:8]
    )

    new_arrivals = (
        Product.objects.filter(is_active=True)
        .order_by("-created_at")[:8]
    )

    return render(
        request,
        "core/home.html",
        {
            "featured": featured,
            "new_arrivals": new_arrivals,
        },
    )