from django import forms

class RegisterForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    nombre = forms.CharField(max_length=50, required=False)     # 👈 agregado
    apellido = forms.CharField(max_length=50, required=False)   # 👈 agregado
    direccion = forms.CharField(max_length=255, required=False)
    telefono = forms.CharField(max_length=20, required=False)
