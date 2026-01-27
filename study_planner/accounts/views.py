from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from .models import User, StudentProfile


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        user = authenticate(request, email=email, password=password)
        print(user)
        if user:
            login(request, user)

            if not remember:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(60 * 60 * 24 * 14)

            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password')

    return render(request, 'accounts/login.html')

def register_view(request):
    if request.method == "POST":
        email = request.POST["email"]
        password1 = request.POST["password1"]
        password2 = request.POST["password2"]

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("register")
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        user = User.objects.create_user(
            email=email,
            password=password1,
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
        )

        StudentProfile.objects.create(
            user=user,
            study_hours_per_day=request.POST.get("study_hours_per_day", 4),
            learning_pace=request.POST.get("learning_pace", "medium"),
        )

        login(request, user)
        return redirect("dashboard")

    return render(request, "accounts/register.html")


def logout_view(request):
    logout(request)
    return redirect('dashboard')


