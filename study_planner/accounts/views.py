from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from .models import User, StudentProfile


def login_view(request):
    if request.user.is_authenticated:
        return redirect('scheduler:dashboard')

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

            return redirect('scheduler:dashboard')
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
            learning_pace=request.POST.get("learning_pace", "medium"),
        )

        login(request, user)
        return redirect("scheduler:dashboard")

    return render(request, "accounts/register.html")

from django.contrib.messages import get_messages

def logout_view(request):
    storage = get_messages(request)
    
    for message in storage:
        pass 
    
    logout(request)

    return redirect('accounts:login') 


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
@login_required
def settings_view(request):
    user = request.user
    profile = user.profile  # Get the OneToOne profile
    
    if request.method == "POST":
        # 1. Update User model fields
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        
        new_email = request.POST.get('email')
        # Basic check to prevent duplicate emails if they change it
        if new_email and new_email != user.email:
            from .models import User
            if User.objects.filter(email=new_email).exists():
                messages.error(request, "This email is already in use by another account.")
            else:
                user.email = new_email

        # 2. Update StudentProfile fields
        profile.email_notifications = 'email_notify' in request.POST
        profile.push_notifications = 'push_notify' in request.POST
        
        # --- ADDED LEARNING PACE LOGIC ---
        new_pace = request.POST.get('learning_pace')
        if new_pace in ['slow', 'medium', 'fast']:
            profile.learning_pace = new_pace
        
        # 3. Save both
        user.save()
        profile.save()
        
        messages.success(request, "Settings updated successfully!")
        return redirect('accounts:settings')

    return render(request, "accounts/settings.html")