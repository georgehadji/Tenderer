from django.contrib import admin
from django.urls import path
from django_otp.admin import OTPAdminSite

# The admin needs a verified second factor (TOTP, or a sealed static code for break-glass) on top of the password,
# behind the identity-aware proxy (§9, §10.2): defence in depth.
admin.site.__class__ = OTPAdminSite

urlpatterns = [path("admin/", admin.site.urls)]
