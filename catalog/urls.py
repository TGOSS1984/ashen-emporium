from django.urls import path
from .views import product_list, product_detail

urlpatterns = [
    path("catalogue/", product_list, name="product_list"),
    path("catalogue/<slug:slug>/", product_detail, name="product_detail"),
]
