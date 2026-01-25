from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Product
from .models import ArmourSet


def product_list(request):
    qs = Product.objects.filter(is_active=True)

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    rarity = request.GET.get("rarity", "").strip()
    in_stock = request.GET.get("in_stock", "").strip()
    sort = request.GET.get("sort", "name").strip()
    subtype = request.GET.get("subtype", "").strip()



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

    if subtype in dict(Product.Subtype.choices):
        qs = qs.filter(subtype=subtype)


    sort_map = {
    "name": "name",
    "price_asc": "price_pence",
    "price_desc": "-price_pence",
    "rarity": "rarity",
    "newest": "-created_at",
    }

    qs = qs.order_by(sort_map.get(sort, "name"))


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
        "sort": sort,
        "subtype": subtype,
        "subtype_choices": Product.Subtype.choices,

    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.filter(is_active=True).prefetch_related("images__asset"),
        slug=slug,
    )
    return render(request, "catalog/product_detail.html", {"product": product})


def armour_set_list(request):
    sets = ArmourSet.objects.all().select_related("hero_image")
    return render(request, "catalog/armour_set_list.html", {"sets": sets})


def armour_set_detail(request, slug):
    armour_set = get_object_or_404(
        ArmourSet.objects.select_related("hero_image").prefetch_related(
            "pieces__images__asset"
        ),
        slug=slug,
    )

    # Sort pieces by common slot order for nicer display
    slot_order = ["helm", "helmet", "hood", "hat", "mask", "crown",
                  "armor", "armour", "robe", "garb", "coat", "cuirass", "chest",
                  "gauntlets", "gloves", "bracers", "manchettes",
                  "greaves", "boots", "trousers", "leggings", "legwraps"]
    def rank(p):
        name = (p.name or "").lower()
        for i, w in enumerate(slot_order):
            if w in name:
                return i
        return 999

    pieces = sorted(list(armour_set.pieces.all()), key=rank)

    return render(
        request,
        "catalog/armour_set_detail.html",
        {"armour_set": armour_set, "pieces": pieces},
    )
