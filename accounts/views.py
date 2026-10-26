from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import CustomUser
from .helpers import send_confirmation_email, make_confirmation_code


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    error = ''
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        role = request.POST.get('role', '')
        if not first_name or not email or not password:
             error = 'Заполни имя, email и пароль.'
        elif role not in ['driver', 'passenger']:
            error = 'Выбери роль.'
        elif CustomUser.objects.filter(email__iexact=email).exists():
            error = 'Этот email уже зарегистрирован.'
        elif len(password) < 8:
            error = 'Пароль должен быть не короче 8 символов.'
        else:
            user = CustomUser.objects.create_user(
                username=email, email=email, password=password,
                first_name=first_name, role=role, is_active=False
            )
            code = make_confirmation_code()
            try:
                send_confirmation_email(email, code)
            except Exception:
                user.delete()
                error = 'Не удалось отправить письмо. Проверь Gmail.'
            else:
                request.session['confirm_user_id'] = user.id
                request.session['confirm_code'] = code
                return redirect('confirm')
    return render(request, 'register.html', {'error': error})

def confirm_view(request):
    user_id = request.session.get('confirm_user_id')
    if not user_id:
        return redirect('register')
    error = ''
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if code == request.session.get('confirm_code'):
            user = CustomUser.objects.filter(id=user_id).first()
            if user is None:
                return redirect('register')
            user.is_active = True
            user.save()
            del request.session['confirm_user_id']
            del request.session['confirm_code']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
        error = 'Неверный код.'
    return render(request, 'confirm.html', {'error': error})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    error = ''
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        error = 'Неверная почта или пароль (или почта не подтверждена).'
    return render(request, 'login.html', {'error': error})

@login_required
def home_view(request):
    return render(request, 'home.html')

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    return redirect('home')