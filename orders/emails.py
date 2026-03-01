from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_order_paid_email(order) -> None:
    """
    Sends order confirmation email (paid).
    Assumes order.email is the customer email.
    """
    subject = f"Ashen Emporium — Order #{order.id} confirmed"
    to_email = order.email

    context = {"order": order}

    text_body = render_to_string("orders/emails/order_paid.txt", context)
    html_body = render_to_string("orders/emails/order_paid.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()