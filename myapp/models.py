from django.db import models

# Create your models here.
class Person(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField(default='example@example.com')

    def __str__(self):
        return self.nom
class Type(models.Model):
    nom = models.CharField(max_length=50)
class Pokemon(models.Model):
    nom = models.CharField(max_length=100)
    image = models.CharField(max_length=100)
    type1 = models.ForeignKey(Type, on_delete=models.SET_NULL, null=True, related_name='primary_type')
    type2 = models.ForeignKey(Type, on_delete=models.SET_NULL, null=True, blank=True, related_name='secondary_type')
    hp = models.IntegerField()
    attaque = models.IntegerField()
    defense = models.IntegerField()
    sp_attaque = models.IntegerField()
    sp_defense = models.IntegerField()
    speed = models.IntegerField()
    recovery = models.IntegerField()
    generation = models.IntegerField()
    catchphrase = models.CharField(max_length=100)

    def __str__(self):
        return self.nom


class User(models.Model):
    nom_utilisateur = models.CharField(max_length=100)
    email = models.EmailField()
    mot_de_passe = models.CharField(max_length=100)

    def __str__(self):
        return self.nom_utilisateur

class Equipe(models.Model):
    nom = models.CharField(max_length=100)
    dresseur = models.ForeignKey(User, on_delete=models.CASCADE)
    pokemons = models.ManyToManyField(Pokemon)

    def __str__(self):
        return self.nom

