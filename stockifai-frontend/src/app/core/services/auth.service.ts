import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';

interface User {
  id: number;
  username: string;
  email: string;
  taller?: any;
  grupo?: any;
  rol_en_grupo?: string;
  is_superuser?: boolean; // ← AGREGAR
  is_staff?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  private readonly API_URL = 'http://localhost:8000/api';

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.checkSession();
  }

  // Redirigir a Auth0 para login
  login(email: string, password: string): Observable<any> {
  return this.http.post(`${this.API_URL}/login-credentials/`, {
    email,
    password
  }, {
    withCredentials: true
  }).pipe(
    tap((response: any) => {
      console.log('✅ Response del backend:', response);  // ← DEBUG
      this.currentUserSubject.next(response.user);
      localStorage.setItem('user', JSON.stringify(response.user));
      console.log('✅ Usuario guardado en localStorage');  // ← DEBUG
    })
  );
}
  // Verificar si hay sesión activa
  checkSession(): Observable<any> {
    return this.http.get(`${this.API_URL}/check-session/`, {
      withCredentials: true
    }).pipe(
      tap((response: any) => {
        if (response.authenticated) {
          this.currentUserSubject.next(response);
          localStorage.setItem('user', JSON.stringify(response));
        }
      })
    );
  }

  logout(): void {
    this.http.post(`${this.API_URL}/logout/`, {}, {
        withCredentials: true
    }).subscribe({
        next: (response: any) => {
            console.log('🔍 URL de logout:', response.logout_url);  // ← AGREGAR ESTO
            console.log('🔍 Respuesta completa:', response);        // ← Y ESTO

            this.currentUserSubject.next(null);
            localStorage.removeItem('user');

            // Redirigir a logout de Auth0
            window.location.href = response.logout_url;
        },
        error: (err) => {
            console.error('Error al cerrar sesión:', err);
            this.currentUserSubject.next(null);
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
    });
}

  isLoggedIn(): boolean {
    return this.currentUserSubject.value !== null;
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }
}
