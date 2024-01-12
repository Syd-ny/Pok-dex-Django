from django.shortcuts import render
from rest_framework import viewsets
from .models import Pokemon
from .serializers import PokemonSerializer

# Create your views here.
class PokemonViewSet(viewsets.ModelViewSet):
    queryset = Pokemon.objects.all()
    serializer_class = PokemonSerializer


def pokemon_list(request):

    # Utilisez la classe PokemonViewSet pour récupérer la liste des Pokémon
    pokemon_viewset = PokemonViewSet()
    queryset = pokemon_viewset.get_queryset()

    # Utilisez le sérialiseur pour transformer les objets en données JSON
    serializer = PokemonSerializer(queryset, many=True)
    pokemon_data = serializer.data

    # Passez les données au template
    return render(request, 'index.html', {'pokemon_data': pokemon_data})

def pokemon_detail(request, pokemon_id):

    # Récupérer le Pokémon en fonction de l'ID
    pokemon = Pokemon.objects.get(pk=pokemon_id)

    # Passer le Pokémon au template
    return render(request, 'pokemon_detail.html', {'pokemon': pokemon})
