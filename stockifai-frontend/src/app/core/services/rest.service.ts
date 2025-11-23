import { HttpClient, HttpHeaders, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, Observable, throwError } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class RestService {
     private baseUrl = 'http://3.137.136.34:8000/api/';

    constructor(private http: HttpClient) {}

    get<T>(endpoint: string, params?: any, headers?: Record<string, string>): Observable<T> {
        return this.http
            .get<T>(`${this.baseUrl}${endpoint}`, {
                params,
                headers: new HttpHeaders(headers || {}),
                withCredentials: true  // ← AGREGAR
            })
            .pipe(catchError((err) => throwError(() => err)));
    }

    post<T>(endpoint: string, body: any, headers?: Record<string, string>): Observable<T> {
        return this.http
            .post<T>(`${this.baseUrl}${endpoint}`, body, {
                headers: new HttpHeaders(headers || {}),
                withCredentials: true
            })
            .pipe(catchError((err) => throwError(() => err)));
    }

    put<T>(endpoint: string, body: any, headers?: Record<string, string>): Observable<T> {
        return this.http
            .put<T>(`${this.baseUrl}${endpoint}`, body, {
                headers: new HttpHeaders(headers || {}),
                withCredentials: true
            })
            .pipe(catchError((err) => throwError(() => err)));
    }

    delete<T>(endpoint: string, params?: any, headers?: Record<string, string>): Observable<T> {
        return this.http
            .delete<T>(`${this.baseUrl}${endpoint}`, {
                params,
                headers: new HttpHeaders(headers || {}),
                withCredentials: true
            })
            .pipe(catchError((err) => throwError(() => err)));
    }

    upload<T>(endpoint: string, formData: FormData, headers?: Record<string, string>): Observable<T> {
        return this.http
            .post<T>(`${this.baseUrl}${endpoint}`, formData, {
                headers: new HttpHeaders(headers || {}),
                withCredentials: true
            })
            .pipe(catchError((err) => throwError(() => err)));
    }

    getBlobResponse(endpoint: string, params?: any): Observable<HttpResponse<Blob>> {
        return this.http
            .get(`${this.baseUrl}${endpoint}`, {
                params,
                responseType: 'blob',
                observe: 'response',
                withCredentials: true
            })
            .pipe(catchError((err) => throwError(() => err)));
    }
}
