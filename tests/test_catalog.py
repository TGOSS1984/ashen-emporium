import pytest
from django.urls import reverse
from catalog.models import Product


@pytest.mark.django_db
def test_catalogue_list_loads(client, product):
    url = reverse("product_list")
    res = client.get(url)
    assert res.status_code == 200
    assert product.name.encode() in res.content


@pytest.mark.django_db
def test_catalogue_filter_by_category(client):
    Product.objects.create(
        sku="WEP_001",
        name="Test Sword",
        category=Product.Category.WEAPON,
        rarity=Product.Rarity.COMMON,
        subtype=Product.Subtype.SWORD,
        price_pence=1000,
        stock_qty=5,
        is_active=True,
    )
    url = reverse("product_list")
    res = client.get(url, {"category": "weapon"})
    assert res.status_code == 200
    assert b"Test Sword" in res.content


@pytest.mark.django_db
def test_catalogue_filter_by_subtype(client):
    Product.objects.create(
        sku="SPL_001",
        name="Test Sorcery",
        category=Product.Category.SPELL,
        rarity=Product.Rarity.COMMON,
        subtype=Product.Subtype.SORCERY,
        price_pence=1000,
        stock_qty=5,
        is_active=True,
    )
    url = reverse("product_list")
    res = client.get(url, {"subtype": "sorcery"})
    assert res.status_code == 200
    assert b"Test Sorcery" in res.content
