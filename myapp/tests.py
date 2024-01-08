from django.test import TestCase
from .models import User, Pokemon, PokemonInstance
from .pokemon_capture import capture_pokemon
from .pokemon_battle import PokemonCombat

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

class PokemonCombatTests(TestCase):
    def setUp(self):
        # Créer des instances de Pokémon pour les tests
        self.pokemon1 = PokemonInstance(nom="Bulbasaur", hp=45, attaque=49, defense=49, speed=45, recovery=5)
        self.pokemon2 = PokemonInstance(nom="Charmander", hp=39, attaque=52, defense=43, speed=65, recovery=4)
        self.combat = PokemonCombat(self.pokemon1, self.pokemon2)

    def test_calculer_vitesse(self):
        vitesse = self.combat.calculer_vitesse(self.pokemon1)
        self.assertTrue(self.pokemon1.speed // 2 <= vitesse <= self.pokemon1.speed)

    def test_calculer_degats(self):
        degats = self.combat.calculer_degats(self.pokemon1, self.pokemon2)
        # Testez si les dégâts sont dans un intervalle attendu (selon votre formule)

    def test_gestion_ko_et_deces(self):
        self.pokemon2.hp = 0
        self.combat.verifier_et_gestionner_ko()
        self.assertTrue(self.pokemon2.ko)

        self.pokemon2.hp = -10
        self.combat.verifier_deces(self.pokemon2)
        # Testez si le Pokémon est décédé ou non (ceci pourrait nécessiter plusieurs essais en raison de la nature aléatoire)