from django.test import TestCase
from .models import User, Pokemon
from .pokemon_capture import capture_pokemon

class PokemonCaptureTest(TestCase):
    def setUp(self):
        # Créez un utilisateur et un Pokémon pour le test
        User.objects.create(nom_utilisateur="testuser", email="test@example.com", mot_de_passe="password")
        Pokemon.objects.create(
            nom="Bulbasaur",
            hp=45,
            attaque=49,
            defense=49,
            sp_attaque=65,
            sp_defense=65,
            speed=45,
            recovery=5,
            generation=1  # Ajoutez une valeur pour 'generation'
        )

    def test_capture_pokemon(self):
        user = User.objects.get(nom_utilisateur="testuser")
        pokemon = Pokemon.objects.get(nom="Bulbasaur")
        pokemon_captured = capture_pokemon(user, pokemon.id)

        # Vérifiez que le Pokémon a été correctement capturé
        self.assertIsNotNone(pokemon_captured)
        self.assertEqual(pokemon_captured.user, user)
        self.assertEqual(pokemon_captured.pokemon, pokemon)
        # Ajoutez plus de vérifications ici selon vos besoins
