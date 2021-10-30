from django.urls import path
from home.views import *


urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("detail/", DetailView.as_view(), name="detail"),
]