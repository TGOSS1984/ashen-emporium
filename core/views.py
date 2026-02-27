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


def about(request):
    return render(request, "core/about.html")


def faq(request):
    return render(request, "core/faq.html")


def origin_stories(request):
    return render(request, "core/origin_stories.html")


def shipping(request):
    return render(request, "core/shipping.html")


def returns(request):
    return render(request, "core/returns.html")


def privacy_policy(request):
    return render(request, "core/privacy_policy.html")


def terms(request):
    return render(request, "core/terms.html")