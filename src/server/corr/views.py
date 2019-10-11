from django.shortcuts import render

# Create your views here.
from django.views.generic import TemplateView


class TestView(TemplateView):
    template_name = 'index_temp.html'
