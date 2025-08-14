import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class RestService {
    private baseUrl = 'http://127.0.0.1:8000/api/';

    constructor(private http: HttpClient) {}

    // Usamos firstValueFrom para convertir los Observables en Promises
    async get<T>(endpoint: string, params?: any, headers?: any): Promise<T> {
        try {
            return await firstValueFrom(
                this.http.get<T>(`${this.baseUrl}${endpoint}`, {
                    params,
                    headers: new HttpHeaders(headers || {}),
                })
            );
        } catch (error) {
            return Promise.reject(error);
        }
    }

    async post<T>(endpoint: string, body: any, headers?: any): Promise<T> {
        try {
            return await firstValueFrom(
                this.http.post<T>(`${this.baseUrl}${endpoint}`, body, {
                    headers: new HttpHeaders(headers || {}),
                })
            );
        } catch (error) {
            return Promise.reject(error);
        }
    }

    async put<T>(endpoint: string, body: any, headers?: any): Promise<T> {
        try {
            return await firstValueFrom(
                this.http.put<T>(`${this.baseUrl}${endpoint}`, body, {
                    headers: new HttpHeaders(headers || {}),
                })
            );
        } catch (error) {
            return Promise.reject(error);
        }
    }

    async delete<T>(endpoint: string, params?: any, headers?: any): Promise<T> {
        try {
            return await firstValueFrom(
                this.http.delete<T>(`${this.baseUrl}/${endpoint}`, {
                    params,
                    headers: new HttpHeaders(headers || {}),
                })
            );
        } catch (error) {
            return Promise.reject(error);
        }
    }

    async upload<T>(endpoint: string, formData: FormData, headers?: any): Promise<T> {
        try {
            return await firstValueFrom(
                this.http.post<T>(`${this.baseUrl}${endpoint}`, formData, {
                    headers: new HttpHeaders(headers || {}),
                })
            );
        } catch (error) {
            return Promise.reject(error);
        }
    }
}
