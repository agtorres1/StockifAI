import { Component, ViewEncapsulation } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class LoginComponent {
  loginForm: FormGroup;
  showPassword = false;
  isSubmitting = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private router: Router
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required]],
      rememberMe: [false]
    });
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  isFormValid() {
    return this.loginForm.valid;
  }

  hasError(fieldName: string, errorType: string): boolean {
    const field = this.loginForm.get(fieldName);
    return !!(field?.touched && field?.errors?.[errorType]);
  }

  isFieldInvalid(fieldName: string): boolean {
    const field = this.loginForm.get(fieldName);
    return !!(field?.touched && field?.invalid);
  }

  async onSubmit() {
    // Marcar todos los campos como tocados
    Object.keys(this.loginForm.controls).forEach(key => {
      this.loginForm.get(key)?.markAsTouched();
    });

    if (!this.loginForm.valid) {
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    const { email, password, rememberMe } = this.loginForm.value;

    try {
      const res: any = await this.http.post('/api/login/', {
        email,
        password,
        rememberMe
      }).toPromise();

      console.log('Login exitoso:', res);

      // Guardar token o datos de sesión
      if (res.token) {
        localStorage.setItem('auth_token', res.token);
      }

      // Redirigir al dashboard o página principal
      this.router.navigate(['/dashboard']);

    } catch (err: any) {
      console.error('Error al iniciar sesión:', err);

      if (err.status === 401) {
        this.errorMessage = 'Email o contraseña incorrectos';
      } else if (err.status === 0) {
        this.errorMessage = 'No se pudo conectar con el servidor';
      } else {
        this.errorMessage = err.error?.error || 'Error al iniciar sesión';
      }
    } finally {
      this.isSubmitting = false;
    }
  }
}
