import random

class PokemonCombat:
    def __init__(self, pokemon1, pokemon2):
        self.pokemon1 = pokemon1
        self.pokemon2 = pokemon2
        self.hp_accumulator_p1 = 0
        self.hp_accumulator_p2 = 0
        self.speed_accumulator_p1 = 0
        self.speed_accumulator_p2 = 0
        self.recovery_accumulator_p1 = 0
        self.recovery_accumulator_p2 = 0

    def calculer_vitesse(self, pokemon):
        return random.randint(pokemon.speed // 2, pokemon.speed)

    def calculer_recovery(self, pokemon):
        return random.randint(pokemon.recovery // 2, pokemon.recovery)

    def calculer_degats(self, attaquant, defenseur):
        modificateur_type = self.determiner_modificateur(attaquant, defenseur)
        degats = (random.randint(attaquant.attaque // 5, attaquant.attaque) / random.randint(defenseur.defense, defenseur.defense * 2)) * modificateur_type
        return max(1, round(degats))  # Arrondi à l'entier supérieur et minimum 1

    def determiner_modificateur(self, attaquant, defenseur):
        # Implémentez la logique de modificateur de type ici
        return 1  # Placeholder

    def combat_tour(self):
        self.speed_accumulator_p1 += self.calculer_vitesse(self.pokemon1)
        self.speed_accumulator_p2 += self.calculer_vitesse(self.pokemon2)

        if self.speed_accumulator_p1 >= 1000:
            self.pokemon2.hp -= self.calculer_degats(self.pokemon1, self.pokemon2)
            self.speed_accumulator_p1 = 0

        if self.speed_accumulator_p2 >= 1000:
            self.pokemon1.hp -= self.calculer_degats(self.pokemon2, self.pokemon1)
            self.speed_accumulator_p2 = 0

    def recovery_tour(self):
        self.recovery_accumulator_p1 += self.calculer_recovery(self.pokemon1)
        self.recovery_accumulator_p2 += self.calculer_recovery(self.pokemon2)

        if self.recovery_accumulator_p1 >= 400:
            self.pokemon1.hp = min(self.pokemon1.hp_max, self.pokemon1.hp + self.calculer_recovery(self.pokemon1))
            self.recovery_accumulator_p1 = 0

        if self.recovery_accumulator_p2 >= 400:
            self.pokemon2.hp = min(self.pokemon2.hp_max, self.pokemon2.hp + self.calculer_recovery(self.pokemon2))
            self.recovery_accumulator_p2 = 0

        self.verifier_et_gestionner_ko()

    def verifier_et_gestionner_ko(self):
        if self.pokemon1.hp <= 10:
                self.gerer_ko(self.pokemon1)

        if self.pokemon2.hp <= 0:
                self.gerer_ko(self.pokemon2)

    def gerer_ko(self, pokemon):
        pokemon.ko = True  # Marque le Pokémon comme KO
        if pokemon.hp < 0:
            # Si la santé est inférieure à 0, vérifiez si le Pokémon décède
            self.verifier_deces(pokemon)

    def verifier_deces(self, pokemon):
        hp_negatifs = abs(pokemon.hp)
        chance_deces = hp_negatifs
        
        while chance_deces > 0:
            jet = random.randint(0, 10000)
            if jet < chance_deces:  # Condition de décès avec probabilité croissante
                pokemon.decede = True
                break
            chance_deces -= 1  # Diminue la probabilité pour le prochain jet