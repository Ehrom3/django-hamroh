from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, default="passenger")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
class Trip(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    car_brand = models.CharField(max_length=100)
    car_year = models.PositiveIntegerField()
    car_photo = models.ImageField(upload_to='cars/')
    start_location = models.CharField(max_length=150)
    end_location = models.CharField(max_length=150)
    date = models.DateTimeField()
    seats_available = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=9, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.start_location
    
class CompanionRequest(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user 
