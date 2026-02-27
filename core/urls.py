from django.urls import path
from .views import home, about, faq

urlpatterns = [
    path("", home, name="home"),
    path("about/", about, name="about"),
    path("faqs/", faq, name="faqs"),
]
