// src/app/session/callback/callback.component.ts
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-callback',
  template: '<div>Verificando sesión...</div>'
})


export class CallbackComponent implements OnInit {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    // Verificar sesión después del callback de Auth0
    this.authService.checkSession().subscribe({
      next: (response) => {
        if (response.authenticated) {
          this.router.navigate(['/dashboard']);
        } else {
          this.router.navigate(['/auth/login']);
        }
      },
      error: () => {
        this.router.navigate(['/auth/login']);
      }
    });
  }
}
