from django.shortcuts import redirect, render
from catalog.models import Product
from django.urls import reverse, NoReverseMatch

from django.contrib import messages

from .forms import ContactForm


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


def sitemap_view(request):
    """
    Used AI to support with sitemap function
    Auto-generated sitemap built from named routes.
    Optionally adds dynamic sections if available (without crashing if not).
    """
    groups = {
        "Shop": [
            ("Browse Catalog", "catalog_product_list"),
        ],
        "Information": [
            ("FAQs", "faqs"),
            ("About us", "about"),
            ("Origin Stories", "origin_stories"),
            ("Privacy Policy", "privacy_policy"),
            ("Terms of Service", "terms"),
            ("Sitemap", "sitemap"),
        ],
        "Customer Services": [
            ("Shipping", "shipping"),
            ("Returns & Refunds", "returns"),
            ("Contact us", "contact"),  # we’ll build later
        ],
    }

    # Turn route names into URLs safely (skip anything not yet implemented)
    sitemap = {}
    for group, items in groups.items():
        resolved = []
        for label, url_name in items:
            try:
                resolved.append({"label": label, "url": reverse(url_name)})
            except NoReverseMatch:
                # Route not implemented yet (e.g., contact)
                continue
        sitemap[group] = resolved

    # Optional dynamic add-ons (only if you have these models/routes)
    # Example: categories list (if your catalog app has Category model + category route)
    dynamic = {}

    try:
        # Adjust import path if your app/model differs
        from catalog.models import Category  # type: ignore

        categories = Category.objects.all().order_by("name")[:50]
        dyn_items = []
        for c in categories:
            # If you have a category page route, swap url_name accordingly:
            # e.g. reverse("category_detail", kwargs={"slug": c.slug})
            # This tries common patterns safely.
            url = None
            for candidate in ("category_detail", "catalog_category_detail"):
                try:
                    url = reverse(candidate, kwargs={"slug": c.slug})
                    break
                except Exception:
                    continue
            if url:
                dyn_items.append({"label": c.name, "url": url})

        if dyn_items:
            dynamic["Categories"] = dyn_items

    except Exception:
        pass

    return render(
        request,
        "core/sitemap.html",
        {"sitemap": sitemap, "dynamic": dynamic},
    )

def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # We’ll send email in Commit B — for now just show success
            messages.success(request, "Message received — the Emporium will respond soon.")
            return redirect("contact")
    else:
        form = ContactForm()

    return render(request, "core/contact.html", {"form": form})