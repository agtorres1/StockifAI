import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  registroForm: FormGroup;
  formValid = false;
  successMessageVisible = false;

  constructor(private fb: FormBuilder, private http: HttpClient) {
    this.registroForm = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(2)]],
      apellido: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      telefono: [''],
      direccion: ['', [Validators.required, Validators.minLength(10)]],
    });

    this.registroForm.statusChanges.subscribe(status => {
      this.formValid = status === 'VALID';
    });
  }

  togglePassword() {
    const pass = document.getElementById('password') as HTMLInputElement;
    if (pass.type === 'password') pass.type = 'text';
    else pass.type = 'password';
  }

  async onSubmit() {
    if (!this.registroForm.valid) return;

    const data = this.registroForm.value;

    try {
      const res: any = await this.http.post('/api/register/', data).toPromise();
      console.log('Usuario creado:', res);
      this.successMessageVisible = true;
      this.registroForm.reset();
    } catch (err) {
      console.error('Error al enviar:', err);
      alert('No se pudo conectar con el servidor');
    }
  }
}
