from django import forms

class RegisterForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    nombre = forms.CharField(max_length=50, required=False)
    apellido = forms.CharField(max_length=50, required=False)
    # Cambiar estos campos:
    calle = forms.CharField(max_length=255, required=False)  # Era "direccion"
    ciudad = forms.CharField(max_length=100, required=False)  # NUEVO
    codigo_postal = forms.CharField(max_length=20, required=False)  # NUEVO
    telefono = forms.CharField(max_length=20, required=False)