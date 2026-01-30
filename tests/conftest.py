import pytest
from django.contrib.auth.models import User

from catalog.models import Product, ArmourSet


@pytest.fixture
def user(db):
    return User.objects.create_user(username="tester", password="pass12345")


@pytest.fixture
def product(db):
    return Product.objects.create(
        sku="TEST_SKU_001",
        name="Test Relic",
        category=Product.Category.RELIC,
        rarity=Product.Rarity.COMMON,
        subtype=Product.Subtype.OTHER,
        price_pence=1299,
        stock_qty=5,
        is_active=True,
        short_description="A test relic.",
        description="Full test lore.",
    )


@pytest.fixture
def armour_set(db):
    return ArmourSet.objects.create(name="Test Set", slug="test-set")


@pytest.fixture
def armour_piece(db, armour_set):
    # armour piece associated to set
    return Product.objects.create(
        sku="TEST_ARMOUR_001",
        name="Test Helm",
        category=Product.Category.ARMOUR,
        rarity=Product.Rarity.COMMON,
        subtype=Product.Subtype.PLATE,
        price_pence=999,
        stock_qty=3,
        is_active=True,
        armour_set=armour_set,
    )
