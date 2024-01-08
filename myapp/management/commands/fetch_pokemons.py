from django.core.management.base import BaseCommand
import requests
from myapp.models import Pokemon, Type, ObjetType

class Command(BaseCommand):
    help = 'Fetches the first 151 Pokémon and items from PokéAPI'

    def handle(self, *args, **kwargs):
        self.importer_pokemons()
        self.importer_objets_de_pokeapi()

    def importer_pokemons(self, *args, **kwargs):
        base_url = "https://pokeapi.co/api/v2/pokemon/"

        for pokemon_id in range(1, 152):  # 151 premiers Pokémon
            response = requests.get(f"{base_url}{pokemon_id}")
            data = response.json()

            # Création du Pokémon
            pokemon = Pokemon(
                nom=data["name"],
                image=data["sprites"]["front_default"],
                hp_max=data["stats"][0]["base_stat"],
                attaque=data["stats"][1]["base_stat"],
                defense=data["stats"][2]["base_stat"],
                sp_attaque=data["stats"][3]["base_stat"],
                sp_defense=data["stats"][4]["base_stat"],
                speed=data["stats"][5]["base_stat"],
                # Les champs 'recovery' et 'generation' nécessitent des valeurs par défaut ou des données supplémentaires
                recovery=0,  # Mettez à jour en fonction de la logique appropriée
                generation=1,  # Première génération
                catchphrase=""  # Vous devez déterminer comment remplir ce champ
            )

            # Gestion des types
            for type_info in data["types"]:
                type_name = type_info["type"]["name"]
                type_obj, created = Type.objects.get_or_create(nom=type_name)
                if type_info["slot"] == 1:
                    pokemon.type1 = type_obj
                else:
                    pokemon.type2 = type_obj

            pokemon.save()

    def importer_objets_de_pokeapi(self, *args, **options):
        url = "https://pokeapi.co/api/v2/item"  # Remplacez par l'URL correcte si nécessaire
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for item in data['results']:
                nom_objet = item['name']
                ObjetType.objects.get_or_create(nom=nom_objet)
                print(f"Ajouté : {nom_objet}")
        else:
            print("Erreur lors de la récupération des données de PokéAPI")

