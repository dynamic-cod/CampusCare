"""
Authentication views and redirects.
"""

from django.contrib import messages
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import redirect
from django.urls import reverse


def register(request):
    messages.info(request, "Students do not need an account. Submit a complaint using your enrollment number.")
    return redirect("core:complaint_create")


class SubAdminLoginView(DjangoLoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        return reverse("core:dashboard")
