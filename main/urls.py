from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('makeApp/', views.makeApp, name='makeApp'),
    path('history/', views.history, name='history'),
    path('app/<int:app_number>/', views.generated_app, name='app'),
]