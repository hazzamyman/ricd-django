from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.http import HttpResponseRedirect
from django.contrib.auth import views as auth_views


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect('/accounts/login/')


urlpatterns = [
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', logout_view, name='logout'),
    path('api/v1/', include('apps.api.urls')),
    path('', include('apps.ui.urls')),
]
