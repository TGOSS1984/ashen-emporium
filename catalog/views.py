from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Product


def product_list(request):
    qs = Product.objects.filter(is_active=True)

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    rarity = request.GET.get("rarity", "").strip()
    in_stock = request.GET.get("in_stock", "").strip()

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(sku__icontains=q)
            | Q(short_description__icontains=q)
            | Q(description__icontains=q)
        )

    if category in dict(Product.Category.choices):
        qs = qs.filter(category=category)

    if rarity in dict(Product.Rarity.choices):
        qs = qs.filter(rarity=rarity)

    if in_stock == "1":
        qs = qs.filter(stock_qty__gt=0)

    qs = qs.order_by("name")

    paginator = Paginator(qs, 24)  # 24 items per page (nice grid)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q": q,
        "category": category,
        "rarity": rarity,
        "in_stock": in_stock,
        "category_choices": Product.Category.choices,
        "rarity_choices": Product.Rarity.choices,
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.filter(is_active=True).prefetch_related("images__asset"),
        slug=slug,
    )
    return render(request, "catalog/product_detail.html", {"product": product})

