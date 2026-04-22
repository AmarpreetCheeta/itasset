from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from app.views import signup_view, login_view, CustomPasswordChangeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
    path('login/', login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', signup_view, name='signup'),
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    # path('passwordchange-done/', auth_views.PasswordChangeDoneView.as_view(
    #     template_name='registration/password_change_done.html'
    # ), name='password_change_done'),
]