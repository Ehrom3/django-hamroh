from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from .helpers import make_confirmation_code, send_confirmation_email
from .models import CompanionRequest, CustomUser, Trip
from datetime import datetime
from decimal import Decimal


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
            error = 'Заполни имя, почту и пароль.'
        elif role not in ['driver', 'passenger']:
            error = 'Выбери роль.'
        elif CustomUser.objects.filter(email__iexact=email).exists():
            error = 'Такая почта уже зарегистрирована.'
        else:
            user = CustomUser.objects.create_user(
                email=email, password=password, first_name=first_name,
                role=role, is_active=False
            )
            code = make_confirmation_code()
            try:
                send_confirmation_email(email, code)
            except Exception:
                user.delete()
                error = 'Не удалось отправить код. Проверь настройки Gmail.'
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
            user.save(update_fields=['is_active'])
            request.session.pop('confirm_user_id', None)
            request.session.pop('confirm_code', None)
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
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    return redirect('home')


@login_required
def home_view(request):
    return render(request, 'home.html')


def _trip_data(request, require_photo):
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
        if timezone.is_naive(date):
            date = timezone.make_aware(date, timezone.get_current_timezone())
    except (ValueError):
        return None, 'Проверь год, дату, места и цену.'
    if not start or not end or not brand or (require_photo and not photo):
        return None, 'Заполни обязательные поля.'
    if start.casefold() == end.casefold():
        return None, 'Города отправления и назначения должны отличаться.'
    if not 1900 <= year <= timezone.localdate().year + 1:
        return None, 'Некорректный год автомобиля.'
    if seats < 0 or price < 0 or not price.is_finite() or price >= Decimal('10000000'):
        return None, 'Проверь свободные места и цену.'
    if require_photo and seats < 1:
        return None, 'Нужно хотя бы одно место.'
    if date <= timezone.now():
        return None, 'Дата поездки должна быть в будущем.'
    if photo and not (photo.content_type or '').startswith('image/'):
        return None, 'Загрузи изображение автомобиля.'
    return {
        'start_location': start, 'end_location': end, 'car_brand': brand,
        'description': description, 'car_year': year,
        'seats_available': seats, 'price': price, 'date': date, 'photo': photo
    }, ''


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
        data, error = _trip_data(request, require_photo=True)
        if data:
            photo = data.pop('photo')
            Trip.objects.create(user=request.user, car_photo=photo, **data)
            return redirect('my_trips')
    return render(request, 'trip_form.html', {'error': error})


@login_required
def trip_edit_view(request, trip_id):
    if request.user.role != 'driver':
        return redirect('home')
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    error = ''
    if request.method == 'POST':
        data, error = _trip_data(request, require_photo=False)
        if data:
            if data['seats_available'] < 0:
                error = 'Количество мест не может быть отрицательным.'
            else:
                photo = data.pop('photo')
                for field, value in data.items():
                    setattr(trip, field, value)
                if photo:
                    trip.car_photo = photo
                trip.save()
                return redirect('my_trips')
    return render(request, 'trip_form.html', {'trip': trip, 'error': error})


@login_required
def trip_delete_view(request, trip_id):
    if request.user.role != 'driver':
        return redirect('home')
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    if request.method == 'POST':
        trip.delete()
    return redirect('my_trips')


@login_required
def trips_list_view(request):
    trips = Trip.objects.filter(date__gt=timezone.now(), seats_available__gt=0).order_by('date')
    start = request.GET.get('start', '').strip()
    end = request.GET.get('end', '').strip()
    date_text = request.GET.get('date', '').strip()
    error = ''
    if start:
        trips = trips.filter(start_location__icontains=start)
    if end:
        trips = trips.filter(end_location__icontains=end)
    if date_text:
        selected_date = parse_date(date_text)
        if selected_date is None:
            error = 'Неверная дата.'
            trips = trips.none()
        else:
            trips = trips.filter(date__date=selected_date)
    return render(request, 'trips_list.html', {
        'trips': trips, 'start': start, 'end': end,
        'date_text': date_text, 'error': error
    })


@login_required
def trip_detail_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    my_request = None
    if request.user.role == 'passenger':
        my_request = CompanionRequest.objects.filter(trip=trip, user=request.user).first()
    return render(request, 'trip_detail.html', {'trip': trip, 'my_request': my_request})


@login_required
def request_trip_view(request, trip_id):
    if request.user.role != 'passenger':
        return redirect('trips_list')
    if request.method != 'POST':
        return redirect('trip_detail', trip_id=trip_id)
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.date <= timezone.now() or trip.seats_available < 1:
        return redirect('trips_list')
    if CompanionRequest.objects.filter(user=request.user, trip=trip).exists():
        return redirect('trip_detail', trip_id=trip_id)
    CompanionRequest.objects.create(user=request.user, trip=trip)
    return redirect('trip_detail', trip_id=trip_id)


@login_required
def driver_requests_view(request):
    if request.user.role != 'driver':
        return redirect('home')
    requests_list = CompanionRequest.objects.filter(trip__user=request.user).order_by('-created_at')
    return render(request, 'driver_requests.html', {'requests_list': requests_list})


@login_required
def request_decision_view(request, request_id):
    if request.user.role != 'driver':
        return redirect('home')
    if request.method != 'POST':
        return redirect('driver_requests')
    with transaction.atomic():
        item = get_object_or_404(CompanionRequest, id=request_id, trip__user=request.user)
        if item.status != 'pending':
            return redirect('driver_requests')
        action = request.POST.get('action')
        if action == 'accept':
            changed = Trip.objects.filter(
                id=item.trip_id,
                seats_available__gt=0,
                date__gt=timezone.now()
            ).update(seats_available=F('seats_available') - 1)
            if changed == 1:
                item.status = 'accepted'
                item.save(update_fields=['status'])
        elif action == 'reject':
            item.status = 'rejected'
            item.save(update_fields=['status'])
    return redirect('driver_requests')


@login_required
def my_requests_view(request):
    if request.user.role != 'passenger':
        return redirect('home')
    requests_list = CompanionRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_requests.html', {'requests_list': requests_list})


@login_required
def cancel_request_view(request, request_id):
    if request.user.role != 'passenger':
        return redirect('home')
    if request.method == 'POST':
        item = get_object_or_404(CompanionRequest, id=request_id, user=request.user)
        if item.status == 'pending':
            item.delete()
    return redirect('my_requests')


@login_required
def profile_view(request):
    error = ''
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        if not first_name:
            error = 'Имя обязательно.'
        else:
            request.user.first_name = first_name
            request.user.save(update_fields=['first_name'])
            return redirect('profile')
    return render(request, 'profile.html', {'error': error})


@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        return redirect('register')
    return redirect('profile')
