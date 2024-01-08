from django.contrib import admin
from .models import Type, Pokemon, User, Equipe, PokemonInstance, Objet, ObjetType

# Register your models here.
admin.site.register(Type)
admin.site.register(Pokemon)
admin.site.register(PokemonInstance)
admin.site.register(User)
admin.site.register(Equipe)
admin.site.register(Objet)
admin.site.register(ObjetType)