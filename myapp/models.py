from django.db import models
import random

# Create your models here.

class Type(models.Model):
    nom = models.CharField(max_length=50)
class Pokemon(models.Model):
    nom = models.CharField(max_length=100)
    image = models.CharField(max_length=100)
    type1 = models.ForeignKey(Type, on_delete=models.SET_NULL, null=True, related_name='primary_type')
    type2 = models.ForeignKey(Type, on_delete=models.SET_NULL, null=True, blank=True, related_name='secondary_type')
    hp_max = models.IntegerField()
    attaque = models.IntegerField()
    defense = models.IntegerField()
    sp_attaque = models.IntegerField()
    sp_defense = models.IntegerField()
    speed = models.IntegerField()
    recovery = models.IntegerField()
    generation = models.IntegerField(default=1)
    catchphrase = models.CharField(max_length=100)

    def __str__(self):
        return self.nom


class User(models.Model):
    nom_utilisateur = models.CharField(max_length=100)
    email = models.EmailField()
    mot_de_passe = models.CharField(max_length=100)

    def __str__(self):
        return self.nom_utilisateur

class PokemonInstance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE)
    hp_max = models.IntegerField(default=0)
    attaque = models.IntegerField(default=0)
    defense = models.IntegerField(default=0)
    sp_attaque = models.IntegerField(default=0)
    sp_defense = models.IntegerField(default=0)
    speed = models.IntegerField(default=0)
    recovery = models.IntegerField(default=0)
    Status = (
        ('En combat', 'En combat'),
        ('KO', 'KO'),
        ('Mort', 'Mort'),
    )

    def __str__(self):
        return f"{self.pokemon.nom} de {self.user.nom_utilisateur}"



class Equipe(models.Model):
    nom = models.CharField(max_length=100)
    dresseur = models.ForeignKey(User, on_delete=models.CASCADE)
    pokemons = models.ManyToManyField(Pokemon)

    def __str__(self):
        return self.nom

