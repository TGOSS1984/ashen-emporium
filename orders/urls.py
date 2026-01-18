from django.urls import path
from .views import checkout, order_confirmation

urlpatterns = [
    path("checkout/", checkout, name="checkout"),
    path("order/<int:order_id>/", order_confirmation, name="order_confirmation"),
]
