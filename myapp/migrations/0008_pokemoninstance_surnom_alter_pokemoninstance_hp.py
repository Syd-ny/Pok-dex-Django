# Generated by Django 5.0 on 2023-12-23 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0007_rename_hp_pokemon_hp_max_pokemoninstance_hp_max_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pokemoninstance',
            name='surnom',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='pokemoninstance',
            name='hp',
            field=models.IntegerField(default=models.IntegerField(default=0)),
        ),
    ]
