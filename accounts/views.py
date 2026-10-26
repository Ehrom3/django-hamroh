from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import CustomUser
from .helpers import send_confirmation_email, make_confirmation_code
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Trip

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

@login_required
def my_trips_view(request):
    if request.user.role != 'driver':
        return redirect('home')
    trips = Trip.objects.filter(user=request.user).order_by('-date')
    return render(request, 'my_trips.html', {'trips': trips})


@login_required
def trip_create_view(request):
    if request.user.role != 'driver':
        return redirect('home')
    error = ''
    if request.method == 'POST':
        start = request.POST.get('start_location', '').strip()
        end = request.POST.get('end_location', '').strip()
        brand = request.POST.get('car_brand', '').strip()
        description = request.POST.get('description', '').strip()
        photo = request.FILES.get('car_photo')
        try:
            year = int(request.POST.get('car_year', ''))
            seats = int(request.POST.get('seats_available', ''))
            price = Decimal(request.POST.get('price', ''))
            date = datetime.fromisoformat(request.POST.get('date', ''))
            date = timezone.make_aware(date)
        except (ValueError, TypeError, InvalidOperation, OverflowError):
            error = 'Проверь год, дату, места и цену.'
        else:
            if not start or not end or not brand or not photo:
                error = 'Заполни обязательные поля и добавь фото.'
            elif start.casefold() == end.casefold():
                error = 'Города отправления и назначения совпадают.'
            elif year < 1900 or year > timezone.localdate().year + 1:
                error = 'Некорректный год автомобиля.'
            elif seats < 1 or price < 0 or not price.is_finite():
                error = 'Проверь количество мест и цену.'
            elif price >= Decimal('10000000'):
                error = 'Цена слишком большая.'
            elif date <= timezone.now():
                error = 'Дата поездки должна быть в будущем.'
            elif not (photo.content_type or '').startswith('image/'):
                error = 'Загрузи изображение автомобиля.'
            else:
                Trip.objects.create(
                    user=request.user, start_location=start,
                    end_location=end, car_brand=brand,
                    car_year=year, car_photo=photo, date=date,
                    seats_available=seats, price=price,
                    description=description
                )
                return redirect('my_trips')
    return render(request, 'trip_form.html', {'error': error})

@login_required
def trip_edit_view(request, trip_id):
    if request.user.role != 'driver':
        return redirect('home')
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    error = ''
    if request.method == 'POST':
        start = request.POST.get('start_location', '').strip()
        end = request.POST.get('end_location', '').strip()
        brand = request.POST.get('car_brand', '').strip()
        photo = request.FILES.get('car_photo')
        try:
            year = int(request.POST.get('car_year', ''))
            seats = int(request.POST.get('seats_available', ''))
            price = Decimal(request.POST.get('price', ''))
            date = datetime.fromisoformat(request.POST.get('date', ''))
            date = timezone.make_aware(date)
        except (ValueError, TypeError, InvalidOperation, OverflowError):
            error = 'Проверь год, дату, места и цену.'
        else:
            if not start or not end or not brand:
                error = 'Заполни города и марку.'
            elif start.casefold() == end.casefold():
                error = 'Города отправления и назначения совпадают.'
            elif year < 1900 or year > timezone.localdate().year + 1:
                error = 'Некорректный год автомобиля.'
            elif seats < 1 or price < 0 or not price.is_finite():
                error = 'Проверь количество мест и цену.'
            elif price >= Decimal('10000000'):
                error = 'Цена слишком большая.'
            elif date <= timezone.now():
                error = 'Дата поездки должна быть в будущем.'
            elif photo and not (photo.content_type or '').startswith('image/'):
                error = 'Загрузи изображение автомобиля.'
            else:
                trip.start_location = start
                trip.end_location = end
                trip.car_brand = brand
                trip.car_year = year
                trip.date = date
                trip.seats_available = seats
                trip.price = price
                trip.description = request.POST.get('description', '')
                if photo:
                    trip.car_photo = photo
                trip.save()
                return redirect('my_trips')
    return render(request, 'trip_form.html', {
        'trip': trip, 'error': error
    })

@login_required
def trip_delete_view(request, trip_id):
    if request.user.role != 'driver':
        return redirect('home')
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    if request.method == 'POST':
        trip.delete()
    return redirect('my_trips')