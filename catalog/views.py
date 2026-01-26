from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect

from .models import Product
from .models import ArmourSet

from django.contrib import messages
from django.views.decorators.http import require_POST
from cart.cart import Cart



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
    slot_order = [
        "helm", "helmet", "hood", "hat", "mask", "crown",
        "armor", "armour", "robe", "garb", "coat", "cuirass", "chest",
        "gauntlets", "gloves", "bracers", "manchettes",
        "greaves", "boots", "trousers", "leggings", "legwraps"
    ]

    def rank(p):
        name = (p.name or "").lower()
        for i, w in enumerate(slot_order):
            if w in name:
                return i
        return 999

    pieces = sorted(list(armour_set.pieces.all()), key=rank)

    # ✅ AS3.5: Bundle summary + discount display (read-only)
    bundle_discount_rate = 0.10  # 10%

    in_stock_pieces = [p for p in pieces if p.is_active and p.stock_qty > 0]
    out_of_stock_pieces = [p for p in pieces if not (p.is_active and p.stock_qty > 0)]

    pieces_total_pence = sum(p.price_pence for p in in_stock_pieces)

    bundle_discount_pence = int(pieces_total_pence * bundle_discount_rate)
    bundle_total_pence = max(pieces_total_pence - bundle_discount_pence, 0)

    context = {
        "armour_set": armour_set,
        "pieces": pieces,
        "in_stock_pieces": in_stock_pieces,
        "out_of_stock_pieces": out_of_stock_pieces,
        "pieces_total_gbp": f"£{pieces_total_pence/100:,.2f}",
        "bundle_discount_rate": int(bundle_discount_rate * 100),
        "bundle_discount_gbp": f"£{bundle_discount_pence/100:,.2f}",
        "bundle_total_gbp": f"£{bundle_total_pence/100:,.2f}",
    }

    return render(
        request,
        "catalog/armour_set_detail.html",
        context,
    )


@require_POST
def armour_set_add_to_cart(request, slug):
    armour_set = get_object_or_404(
        ArmourSet.objects.prefetch_related("pieces"),
        slug=slug,
    )

    mode = request.POST.get("mode", "all")  # "all" or "missing"
    cart = Cart(request.session)

    # Current cart product IDs as strings (your Cart stores keys as strings)
    cart_data = request.session.get("cart", {})
    in_cart_ids = set(cart_data.keys())

    added = 0
    skipped_out = 0
    skipped_inactive = 0
    skipped_already_in_cart = 0

    for p in armour_set.pieces.all():
        if not p.is_active:
            skipped_inactive += 1
            continue
        if p.stock_qty <= 0:
            skipped_out += 1
            continue

        if mode == "missing" and str(p.id) in in_cart_ids:
            skipped_already_in_cart += 1
            continue

        cart.add(product_id=p.id, qty=1)
        added += 1

    if mode == "missing":
        if added:
            messages.success(request, f"Added {added} missing piece(s) from {armour_set.name}.")
        else:
            messages.info(request, "All available pieces are already in your basket.")
        if skipped_already_in_cart:
            messages.info(request, f"Skipped {skipped_already_in_cart} piece(s) already in your basket.")
    else:
        if added:
            messages.success(request, f"Added {added} piece(s) from {armour_set.name} to your basket.")

    if skipped_out:
        messages.warning(request, f"Skipped {skipped_out} out-of-stock piece(s).")
    if skipped_inactive:
        messages.info(request, f"Skipped {skipped_inactive} unavailable piece(s).")

    return redirect("armour_set_detail", slug=armour_set.slug)

