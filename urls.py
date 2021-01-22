from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from slack import message

urlpatterns = [
    path('admin/', admin.site.urls),
    path('slack/', message.slack_post, name='slack'),
    path('', include('silverstrike.urls')),
]
