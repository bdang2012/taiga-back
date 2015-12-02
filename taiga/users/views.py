from django.shortcuts import render
from django.http import HttpResponse
from django.http import Http404

def binh(request):
    return HttpResponse('<p>binh is in views.py of users</p>')
