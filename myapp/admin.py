from django.contrib import admin
from .models import Person, Type, Pokemon, User, Equipe

# Register your models here.
admin.site.register(Person)
admin.site.register(Type)
admin.site.register(Pokemon)
admin.site.register(User)
admin.site.register(Equipe)
