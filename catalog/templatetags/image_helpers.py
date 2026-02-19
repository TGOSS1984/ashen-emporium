from django import template
from django.templatetags.static import static

register = template.Library()


@register.filter(name="image_or_placeholder")
def image_or_placeholder(image_field):
    """
    Return the image URL if available; otherwise return a static placeholder.
    Defensive against missing files in production.
    """
    placeholder = static("images/placeholder.png")

    if not image_field:
        return placeholder

    try:
        return image_field.url
    except Exception:
        return placeholder
