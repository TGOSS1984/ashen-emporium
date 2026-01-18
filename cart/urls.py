from django.urls import path
from .views import cart_detail, cart_add, cart_update, cart_remove

urlpatterns = [
    path("cart/", cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", cart_remove, name="cart_remove"),
]
