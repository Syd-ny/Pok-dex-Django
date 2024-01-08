# pokemon_capture.py

import random
from .models import PokemonInstance, Pokemon

def randomize_stats(pokemon_base):
    random_factor = 0.15  # 15% de variation par rapport à la stat de base
    recovery = random.randint(1, 10)  # Recovery aléatoire entre 1 et 10
    return {
        'hp_max': int(random.uniform(1-random_factor, 1+random_factor) * pokemon_base.hp_max),
        'attaque': int(random.uniform(1-random_factor, 1+random_factor) * pokemon_base.attaque),
        'defense': int(random.uniform(1-random_factor, 1+random_factor) * pokemon_base.defense),
        'sp_attaque': int(random.uniform(1-random_factor, 1+random_factor) * pokemon_base.sp_attaque),
        'sp_defense': int(random.uniform(1-random_factor, 1+random_factor) * pokemon_base.sp_defense),
        'speed': int(random.uniform(1-random_factor, 1+random_factor) * pokemon_base.speed),
        'recovery': recovery  # Ajoutez la valeur randomisée de recovery
    }
    pass

def capture_pokemon(user, pokemon_id, surnom=None):
    pokemon_base = Pokemon.objects.get(id=pokemon_id)
    stats = randomize_stats(pokemon_base)
    pokemon_instance = PokemonInstance(
        user=user,
        pokemon=pokemon_base,
        hp_max=stats['hp_max'],
        hp=stats['hp_max'],
        attaque=stats['attaque'],
        defense=stats['defense'],
        sp_attaque=stats['sp_attaque'],
        sp_defense=stats['sp_defense'],
        speed=stats['speed'],
        recovery=stats['recovery'],  # Ajoutez le champ recovery
    )
    if surnom:
        pokemon_instance.surnom = surnom
    else:
        pokemon_instance.surnom = pokemon_base.nom
    pokemon_instance.save()
    return pokemon_instance

