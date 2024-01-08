from django import forms
from ..models import PokemonInstance


class SurnomForm(forms.ModelForm):
    class Meta:
        model = PokemonInstance
        fields = ['surnom']
