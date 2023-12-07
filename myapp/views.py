from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index(request):
    context = {'name': "Titi", 'list_articles': ['développement', 'réseau', 'Jeux', 'Informatique']}
    return render(request, 'myapp/index.html', context)

def info(request):
    return HttpResponse("<p>ok</p>")
