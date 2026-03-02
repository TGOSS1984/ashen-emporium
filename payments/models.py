# payments/models.py
from django.db import models


class StripeEvent(models.Model):
    """
    Stores Stripe webhook event ids to guarantee idempotency.
    If Stripe retries the same event, we no-op safely.
    """
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: useful for debugging in admin
    livemode = models.BooleanField(default=False)
    stripe_created = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.event_type} ({self.event_id})"
