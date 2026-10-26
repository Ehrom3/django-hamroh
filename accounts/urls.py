from django.urls import path
from . import views


urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('confirm/', views.confirm_view, name='confirm'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('my-trips/', views.my_trips_view, name='my_trips'),
    path('trips/new/', views.trip_create_view, name='trip_create'),
    path('trips/<int:trip_id>/edit/', views.trip_edit_view, name='trip_edit'),
    path('trips/<int:trip_id>/delete/', views.trip_delete_view, name='trip_delete'),
    path('trips/', views.trips_list_view, name='trips_list'),
    path('trips/<int:trip_id>/', views.trip_detail_view, name='trip_detail'),   

]