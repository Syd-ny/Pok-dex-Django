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
    surnom = models.CharField(max_length=100, blank=True)
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE)
    hp_max = models.IntegerField(default=0) # Santé maximale
    hp = models.IntegerField(default=hp_max)      # Santé actuelle
    attaque = models.IntegerField(default=0)
    defense = models.IntegerField(default=0)
    sp_attaque = models.IntegerField(default=0)
    sp_defense = models.IntegerField(default=0)
    speed = models.IntegerField(default=0)
    recovery = models.IntegerField(default=0)
    status = models.CharField(max_length=50, choices=(
        ('En repos', 'En repos'),
        ('En combat', 'En combat'),
        ('KO', 'KO'),
        ('Mort', 'Mort'),
    ), default='En combat')

    def save(self, *args, **kwargs):
        if not self.surnom:
            self.surnom = self.pokemon.nom  # Initialise avec le nom de l'espèce
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.surnom} de {self.user.nom_utilisateur}"



class Equipe(models.Model):
    nom = models.CharField(max_length=100)
    dresseur = models.ForeignKey(User, on_delete=models.CASCADE)
    pokemons = models.ManyToManyField(Pokemon)

    def __str__(self):
        return self.nom

class ObjetType(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return self.nom
    
class Objet(models.Model):
    type_objet = models.ForeignKey(ObjetType, on_delete=models.CASCADE, related_name='instances')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='objets')
    pokemon = models.OneToOneField(PokemonInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name='objet')

    def __str__(self):
        return f"{self.type_objet.nom} de {self.utilisateur.nom_utilisateur}"
    
class BaieType(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return self.nom
    
class Baie(models.Model):
    type_baie = models.ForeignKey(BaieType, on_delete=models.CASCADE, related_name='instances')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='baies')
    pokemon = models.OneToOneField(PokemonInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name='baie')

    def __str__(self):
        return f"{self.type_baie.nom} de {self.utilisateur.nom_utilisateur}"
