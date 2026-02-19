from django import template
from django.templatetags.static import static

register = template.Library()


@register.filter(name="image_or_placeholder")
def image_or_placeholder(image_field):
    placeholder = static("images/placeholder.png")

    if not image_field:
        return placeholder

    try:
        storage = getattr(image_field, "storage", None)
        name = getattr(image_field, "name", "")

        # If the field is set but the underlying file isn't present, use placeholder
        if storage and name and hasattr(storage, "exists"):
            if not storage.exists(name):
                return placeholder

        return image_field.url
    except Exception:
        return placeholder

