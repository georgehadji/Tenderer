from django.contrib import admin
from django.urls import path

urlpatterns = [path("admin/", admin.site.urls)]  # reachable only through the identity-aware proxy (§9)
