import pytest
from django.urls import reverse
from catalog.models import ArmourSet, Product


@pytest.mark.django_db
def test_armour_set_list_loads(client, armour_set):
    url = reverse("armour_set_list")
    res = client.get(url)
    assert res.status_code == 200
    assert armour_set.name.encode() in res.content


@pytest.mark.django_db
def test_armour_set_detail_loads(client, armour_set, armour_piece):
    url = reverse("armour_set_detail", kwargs={"slug": armour_set.slug})
    res = client.get(url)
    assert res.status_code == 200
    assert armour_set.name.encode() in res.content
    assert armour_piece.name.encode() in res.content
