# Generated by Django 5.0 on 2023-12-18 12:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_pokemoninstance_recovery'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pokemoninstance',
            name='niveau',
        ),
    ]