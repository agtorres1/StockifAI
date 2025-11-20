import { Component, ViewEncapsulation } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class RegisterComponent {
  registroForm: FormGroup;
  formValid = false;

  showSuccessMessage = false;
  showPassword = false;
  isSubmitting = false;

  constructor(private fb: FormBuilder, private http: HttpClient) {
    this.registroForm = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(2)]],
      apellido: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [
        Validators.required,
        Validators.minLength(8),
        this.passwordValidator
      ]],
      telefono: [''],
      direccion: ['', [Validators.required]],
      codigoPostal: ['', [Validators.required]],
      ciudad: ['', [Validators.required]]
    });

    this.registroForm.statusChanges.subscribe(status => {
      this.formValid = status === 'VALID';
    });
  }

  // Validador personalizado para contraseña segura
  passwordValidator(control: AbstractControl): ValidationErrors | null {
    const value = control.value;

    if (!value) {
      return null;
    }

    const hasUpperCase = /[A-Z]/.test(value);
    const hasLowerCase = /[a-z]/.test(value);
    const hasNumeric = /[0-9]/.test(value);
    const hasSpecialChar = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(value);

    const passwordValid = hasUpperCase && hasLowerCase && hasNumeric && hasSpecialChar;

    return !passwordValid ? {
      passwordStrength: {
        hasUpperCase,
        hasLowerCase,
        hasNumeric,
        hasSpecialChar
      }
    } : null;
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  isFormValid() {
    return this.registroForm.valid;
  }

  formatTelefono(event: Event) {
    const input = event.target as HTMLInputElement;
    input.value = input.value.replace(/\D/g, ''); // solo números
  }

  // Método auxiliar para verificar si un campo tiene un error específico
  hasError(fieldName: string, errorType: string): boolean {
    const field = this.registroForm.get(fieldName);
    return !!(field?.touched && field?.errors?.[errorType]);
  }

  // Método auxiliar para verificar si un campo fue tocado y es inválido
  isFieldInvalid(fieldName: string): boolean {
    const field = this.registroForm.get(fieldName);
    return !!(field?.touched && field?.invalid);
  }

  async onSubmit() {
    // Marcar todos los campos como tocados para mostrar errores
    Object.keys(this.registroForm.controls).forEach(key => {
      this.registroForm.get(key)?.markAsTouched();
    });

    if (!this.registroForm.valid) {
      alert('Por favor completá todos los campos correctamente');
      return;
    }

    this.isSubmitting = true;
    const formData = this.registroForm.value;

    // Armar el objeto en el formato que espera tu backend Django
    const data = {
      nombre: formData.nombre,
      apellido: formData.apellido,
      email: formData.email,
      password: formData.password,
      telefono: formData.telefono || '',
      calle: formData.direccion,  // El campo "direccion" del form es la calle
      ciudad: formData.ciudad,
      codigo_postal: formData.codigoPostal
    };

    try {
      const res: any = await this.http.post('/api/register/', data).toPromise();
      this.showSuccessMessage = true;
      this.registroForm.reset();
    } catch (err: any) {
      const errorMsg = err.error?.error || 'No se pudo conectar con el servidor';
      alert(errorMsg);
    } finally {
      this.isSubmitting = false;
    }
  }
}
