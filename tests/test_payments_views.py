import pytest
from django.contrib.auth import get_user_model
from django.urls import URLPattern, URLResolver, get_resolver

from catalog.models import Product

pytestmark = pytest.mark.django_db


def make_product(**overrides) -> Product:
    """
    Create an active Product suitable for payments/cart tests.
    Cart pricing uses price_pence.
    """
    data = {
        "name": "Test Product",
        "sku": "SKU-TEST-1",
        "category": "armour",
        "slug": "test-product",
        "price_pence": 10000,  # £100.00
        "is_active": True,
        **overrides,
    }
    return Product.objects.create(**data)


def make_user(**overrides):
    User = get_user_model()
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "pass12345!",
        **overrides,
    }
    return User.objects.create_user(**data)


def iter_urlpatterns(patterns, prefix=""):
    """
    Yield (full_path, URLPattern) for every URLPattern in the project,
    including included URLconfs.
    """
    for p in patterns:
        if isinstance(p, URLPattern):
            route = str(p.pattern)
            yield prefix + route, p
        elif isinstance(p, URLResolver):
            route = str(p.pattern)
            yield from iter_urlpatterns(p.url_patterns, prefix + route)


def find_payments_paths() -> list[str]:
    """
    Return static URL paths whose callback lives in payments.views.
    Static = no path converters like <int:id>.
    """
    resolver = get_resolver()
    results: list[str] = []

    for path, pattern in iter_urlpatterns(resolver.url_patterns, prefix="/"):
        cb = getattr(pattern, "callback", None)
        if not cb:
            continue

        module = getattr(cb, "__module__", "") or ""
        if not module.startswith("payments.views"):
            continue

        # ignore dynamic paths (can't POST without args)
        if "<" in path or ">" in path:
            continue

        # normalise leading slash
        if not path.startswith("/"):
            path = "/" + path

        results.append(path)

    return results


def pick_create_checkout_path() -> str:
    """
    Choose the most likely 'create checkout session' endpoint path
    from the payments views URL patterns.
    """
    paths = find_payments_paths()

    # Exclude known endpoints we don't want here
    excluded_keywords = ("webhook", "success", "cancel")
    candidates = [
        p for p in paths
        if not any(k in p for k in excluded_keywords)
    ]

    # Prefer paths that look like they create a session/checkout
    preferred = [
        p for p in candidates
        if any(k in p for k in ("checkout", "session", "create", "stripe"))
    ]

    if preferred:
        return preferred[0]

    if candidates:
        return candidates[0]

    # If nothing found, skip rather than fail the whole suite
    pytest.skip(
        "No static payments endpoint found for creating a checkout session "
        "(could be dynamic URL or located outside payments.views)."
    )


def test_payment_success_requires_login(client):
    res = client.get("/payment/success/")
    assert res.status_code == 302
    assert "/account/login/" in res["Location"]
    assert "next=/payment/success/" in res["Location"]


def test_payment_cancel_requires_login(client):
    res = client.get("/payment/cancel/")
    assert res.status_code == 302
    assert "/account/login/" in res["Location"]
    assert "next=/payment/cancel/" in res["Location"]


def test_payment_success_page_when_logged_in(client):
    user = make_user()
    client.force_login(user)

    res = client.get("/payment/success/")
    assert res.status_code == 200


def test_payment_cancel_page_when_logged_in(client):
    user = make_user(username="testuser2", email="test2@example.com")
    client.force_login(user)

    res = client.get("/payment/cancel/")
    assert res.status_code == 200


def test_create_checkout_session_with_cart(monkeypatch, client):
    """
    Finds your create-checkout endpoint by scanning urlpatterns, then POSTs to it.
    Mocks Stripe so no network calls happen.
    """
    user = make_user(username="payer", email="payer@example.com")
    client.force_login(user)

    p = make_product(
        name="Ashen Shield",
        sku="SKU-SHLD-1",
        slug="ashen-shield",
        price_pence=15000,
    )
    # use your known-good cart route name (already passing elsewhere)
    client.post(f"/cart/add/{p.id}/", data={"qty": 1}, follow=True)

    class DummySession:
        url = "https://example.com/checkout-session"

    def dummy_create(*args, **kwargs):
        return DummySession()

    import payments.views as pv
    monkeypatch.setattr(pv.stripe.checkout.Session, "create", dummy_create)

    create_path = pick_create_checkout_path()
    res = client.post(create_path)

    if res.status_code in (302, 303):
        assert res["Location"] == DummySession.url
    else:
        # If it returns JSON
        data = res.json()
        assert data.get("url") == DummySession.url


def test_create_checkout_session_empty_cart_does_not_call_stripe(monkeypatch, client):
    user = make_user(username="payer2", email="payer2@example.com")
    client.force_login(user)

    import payments.views as pv

    def dummy_create(*args, **kwargs):
        raise AssertionError("Stripe should not be called for empty cart")

    monkeypatch.setattr(pv.stripe.checkout.Session, "create", dummy_create)

    create_path = pick_create_checkout_path()
    res = client.post(create_path, follow=True)

    # allow different valid behaviours, just ensure it doesn't crash
    assert res.status_code in (200, 302, 303, 400)