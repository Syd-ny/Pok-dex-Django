from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets
from .models import Pokemon
from .serializers import PokemonSerializer

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Equipe

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
    pokemon = get_object_or_404(Pokemon, pk=pokemon_id)

    # Trouver l'ID du Pokémon précédent
    previous_pokemon = Pokemon.objects.filter(id__lt=pokemon.id).order_by('-id').first()

    # Trouver l'ID du Pokémon suivant
    next_pokemon = Pokemon.objects.filter(id__gt=pokemon.id).order_by('id').first()

    context = {
        'pokemon': pokemon,
        'previous_pokemon': previous_pokemon,
        'next_pokemon': next_pokemon,
    }

    # Passer le Pokémon et les informations sur le précédent et suivant au template
    return render(request, 'pokemon_detail.html', context)


@login_required(login_url='/accounts/login/')
def ajout_equipe(request):
    if request.method == 'POST':
        # Récupérer l'utilisateur actuellement connecté
        dresseur = request.user

        # Créer une nouvelle équipe avec le dresseur approprié
        nouvelle_equipe = Equipe.objects.create(
            nom=request.POST['nom'],
            dresseur=dresseur
        )

        # Ajouter les Pokémon à l'équipe (à compléter selon votre logique)
        selected_pokemons = request.POST.getlist('pokemons')
        nouvelle_equipe.pokemons.set(selected_pokemons)

        return redirect('affichage_equipe')

    return render(request, 'ajout_equipe.html')


def affichage_equipe(request):
    equipes = Equipe.objects.filter()
    return render(request, 'affichage_equipe.html', {'equipes': equipes})
