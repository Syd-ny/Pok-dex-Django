from django.db import models

# Create your models here.
class Pokemon(models.Model):
    nom = models.CharField(max_length=100)
    type1 = models.IntegerField(max.length=50)
    type2 = models.IntegerField(max.length=50, blank=True, null=True)
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

