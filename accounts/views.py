from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import redirect, render


def register(request):
    if request.user.is_authenticated:
        return redirect("account_home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. You can now log in.")
            return redirect("login")
    else:
        form = UserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect("account_home")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Welcome back, Ashen One.")
            return redirect("home")
    else:
        form = AuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})


def user_logout(request):
    # Logout via POST is best practice.
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def account_home(request):
    return render(request, "accounts/account_home.html")
