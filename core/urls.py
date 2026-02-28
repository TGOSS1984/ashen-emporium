from django.urls import path
from .views import (
    home,
    about,
    faq,
    origin_stories,
    shipping,
    returns,
    privacy_policy,
    terms,
    sitemap_view,
    contact,
)

urlpatterns = [
    path("", home, name="home"),
    path("about/", about, name="about"),
    path("faqs/", faq, name="faqs"),
    path("origin-stories/", origin_stories, name="origin_stories"),
    path("shipping/", shipping, name="shipping"),
    path("returns/", returns, name="returns"),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("terms/", terms, name="terms"),
    path("sitemap/", sitemap_view, name="sitemap"),
    path("contact/", contact, name="contact"),
]
