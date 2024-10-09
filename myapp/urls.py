from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PokemonViewSet, pokemon_list, pokemon_detail, ajout_equipe, affichage_equipe

router = DefaultRouter()
router.register(r'pokemon', PokemonViewSet)

urlpatterns = [

    path('', include(router.urls)),
    path('index/', pokemon_list, name='index'),
    path('pokemon-detail/<int:pokemon_id>/', pokemon_detail, name='pokemon_detail'),
    path('ajout-equipe/', ajout_equipe, name='ajout_equipe'),
    path('affichage-equipe/', affichage_equipe, name='affichage_equipe'),

    #path('blog/<str:name>/<int:number>',views.blog, name='blog'),
    #path('info/',views.info, name='info'),
    #path('index/',views.index, name='index'),
]