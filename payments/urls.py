from django.urls import path
from .views import start_checkout, payment_success, payment_cancel, stripe_webhook

urlpatterns = [
    path("pay/<int:order_id>/", start_checkout, name="start_checkout"),
    path("payment/success/", payment_success, name="payment_success"),
    path("payment/cancel/", payment_cancel, name="payment_cancel"),
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
]
