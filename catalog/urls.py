from django.urls import path
from .views import product_list, product_detail

from . import views

urlpatterns = [
    path("catalogue/", product_list, name="product_list"),
    path("catalogue/<slug:slug>/", product_detail, name="product_detail"),
    path("armour-sets/<slug:slug>/add-to-cart/", views.armour_set_add_to_cart, name="armour_set_add_to_cart"),
]

urlpatterns += [
    path("armour-sets/", views.armour_set_list, name="armour_set_list"),
    path("armour-sets/<slug:slug>/", views.armour_set_detail, name="armour_set_detail"),
]