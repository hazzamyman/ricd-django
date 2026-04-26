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
    # Include app URLs
    path('councils/', include('apps.councils.urls')),
    path('programs/', include('apps.programs.urls')),
    path('projects/', include('apps.projects.urls')),
    path('addresses/', include('apps.addresses.urls')),
    path('works/', include('apps.works.urls')),
    path('funding/', include('apps.funding.urls')),
    path('defects/', include('apps.defects.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('variations/', include('apps.variations.urls')),
    path('contractors/', include('apps.contractors.urls')),
    path('planning/', include('apps.planning.urls')),
    path('documents/', include('apps.documents.urls')),
    path('reports/', include('apps.reports.urls')),
    path('maintenance/', include('apps.maintenance.urls')),
    path('contracts/', include('apps.contracts.urls')),
    path('land/', include('apps.land_infra.urls')),
    path('payments/', include('apps.payments.urls')),
]
