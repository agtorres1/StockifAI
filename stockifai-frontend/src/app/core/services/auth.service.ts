import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable } from 'rxjs';
import { distinctUntilChanged, map, shareReplay, tap } from 'rxjs/operators';
import { Taller } from '../models/taller';

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
    providedIn: 'root',
})
export class AuthService {
    private currentUserSubject = new BehaviorSubject<User | null>(null);
    public currentUser$ = this.currentUserSubject.asObservable();

    private activeTallerSubject = new BehaviorSubject<Taller | null>(null);
    public activeTaller$ = this.activeTallerSubject.asObservable();

    public activeTallerId$ = this.activeTaller$.pipe(
        map((taller) => taller?.id ?? null),
        distinctUntilChanged(),
        shareReplay(1)
    );

    private readonly API_URL = 'http://localhost:8000/api';

    private static readonly STORAGE_USER = 'user';
    private static readonly STORAGE_TALLER = 'activeTaller';

    constructor(private http: HttpClient, private router: Router) {
        const tallerRaw = localStorage.getItem(AuthService.STORAGE_TALLER);
        if (tallerRaw) {
            try {
                this.activeTallerSubject.next(JSON.parse(tallerRaw));
            } catch {}
        }

        this.checkSession();
    }

    // Redirigir a Auth0 para login
    login(email: string, password: string): Observable<any> {
        return this.http
            .post(
                `${this.API_URL}/login-credentials/`,
                {
                    email,
                    password,
                },
                {
                    withCredentials: true,
                }
            )
            .pipe(
                tap((response: any) => {
                    console.log('✅ Response del backend:', response); // ← DEBUG
                    this.currentUserSubject.next(response.user);
                    localStorage.setItem(AuthService.STORAGE_USER, JSON.stringify(response.user));

                    const defaultTaller = response?.taller ?? null;
                    if (defaultTaller) {
                        this.setActiveTaller(defaultTaller);
                    }
                })
            );
    }
    // Verificar si hay sesión activa
    checkSession(): Observable<any> {
        return this.http
            .get(`${this.API_URL}/check-session/`, {
                withCredentials: true,
            })
            .pipe(
                tap((response: any) => {
                    if (response.authenticated) {
                        this.currentUserSubject.next(response);
                        localStorage.setItem(AuthService.STORAGE_USER, JSON.stringify(response));

                        const defaultTaller = response?.taller ?? null;
                        if (defaultTaller) {
                            this.setActiveTaller(defaultTaller);
                        }
                    }
                })
            );
    }

    logout(): void {
        this.http
            .post(
                `${this.API_URL}/logout/`,
                {},
                {
                    withCredentials: true,
                }
            )
            .subscribe({
                next: (response: any) => {
                    this.currentUserSubject.next(null);
                    localStorage.removeItem(AuthService.STORAGE_USER);

                    this.setActiveTaller(null);

                    // Redirigir a logout de Auth0
                    window.location.href = response.logout_url;
                },
                error: (err) => {
                    console.error('Error al cerrar sesión:', err);
                    this.currentUserSubject.next(null);
                    localStorage.removeItem(AuthService.STORAGE_USER);
                    this.setActiveTaller(null);
                    window.location.href = '/login';
                },
            });
    }

    isLoggedIn(): boolean {
        return this.currentUserSubject.value !== null;
    }


    setActiveTaller(taller: Taller | null): void {
        this.activeTallerSubject.next(taller);
        if (taller) {
            localStorage.setItem(AuthService.STORAGE_TALLER, JSON.stringify(taller));
        } else {
            localStorage.removeItem(AuthService.STORAGE_TALLER);
        }
    }

    getActiveTaller(): Taller | null {
        return this.activeTallerSubject.value;
    }

  getCurrentUser(): User | null {
    // Si ya está en el BehaviorSubject, usarlo
    if (this.currentUserSubject.value) {
        return this.currentUserSubject.value;
    }

    // Si no, leerlo del localStorage
    const userFromStorage = localStorage.getItem('user');
    if (userFromStorage) {
        const user = JSON.parse(userFromStorage);
        this.currentUserSubject.next(user);  // Actualizar el BehaviorSubject
        return user;
    }

    return null;
}
    public getActiveTallerId(): number | null {
        return this.activeTallerSubject.value?.id ?? null;
    }
}
