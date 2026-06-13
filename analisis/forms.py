# analisis/forms.py

from django import forms
from django.contrib.auth.models import User
from django.forms import TextInput, EmailInput

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': TextInput(attrs={
                'class': "form-control",
                'placeholder': 'Masukkan username baru'
            }),
            'email': EmailInput(attrs={
                'class': "form-control",
                'placeholder': 'Masukkan email baru'
            })
        }