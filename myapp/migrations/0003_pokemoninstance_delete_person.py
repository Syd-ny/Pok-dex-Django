# Generated by Django 5.0 on 2023-12-18 12:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_type_user_rename_name_person_nom_remove_person_age_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PokemonInstance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('niveau', models.IntegerField(default=1)),
                ('hp', models.IntegerField()),
                ('attaque', models.IntegerField()),
                ('defense', models.IntegerField()),
                ('sp_attaque', models.IntegerField()),
                ('sp_defense', models.IntegerField()),
                ('speed', models.IntegerField()),
                ('pokemon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.pokemon')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.user')),
            ],
        ),
        migrations.DeleteModel(
            name='person',
        ),
    ]
