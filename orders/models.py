from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PLACED = "placed", "Placed"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    email = models.EmailField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    total_pence = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    def total_gbp(self) -> str:
        return f"£{self.total_pence/100:,.2f}"

    def __str__(self) -> str:
        return f"Order #{self.id} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product_name = models.CharField(max_length=140)
    sku = models.CharField(max_length=64)

    unit_price_pence = models.PositiveIntegerField()
    qty = models.PositiveIntegerField()

    line_total_pence = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"{self.product_name} x{self.qty}"
