from django.urls import path
from .views import home, about, faq, origin_stories, shipping, returns

urlpatterns = [
    path("", home, name="home"),
    path("about/", about, name="about"),
    path("faqs/", faq, name="faqs"),
    path("origin-stories/", origin_stories, name="origin_stories"),
    path("shipping/", shipping, name="shipping"),
    path("returns/", returns, name="returns"),
]
