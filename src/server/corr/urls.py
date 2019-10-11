from django.urls import path

from corr.views import TestView

app_name = 'corr_app'

urlpatterns = [
    path('', TestView.as_view()),
]