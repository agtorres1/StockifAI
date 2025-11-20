import { Injectable } from '@angular/core';
import { Observable, of, delay } from 'rxjs';

interface CacheEntry<T> {
    value: T;
    exp: number | null; // null = no expira
}

@Injectable({ providedIn: 'root' })
export class CacheService {
    private store = new Map<string, CacheEntry<any>>();

    private defaultTTL = 20 * 60 * 1000; // 20 minutos

    /** Delay mínimo para hits del cache */
    private minDelay = 120; // ms

    /** Obtiene un valor si existe y no expiró */
    get<T>(key: string): Observable<T> | null {
        const entry = this.store.get(key);
        if (!entry) return null;

        if (entry.exp !== null && entry.exp < Date.now()) {
            this.store.delete(key);
            return null;
        }

        // hit → devolvemos observable con delay mínimo
        return of(entry.value).pipe(delay(this.minDelay));
    }

    /** Guarda un valor con TTL opcional */
    set<T>(key: string, value: T, ttlMs: number | null = null) {
        const ttl = ttlMs ?? this.defaultTTL; // si ttlMs es null → usa el global
        const exp = ttl ? Date.now() + ttl : null;
        this.store.set(key, { value, exp });
    }

    /** Borra una clave */
    invalidate(key: string) {
        this.store.delete(key);
    }

    /** Borra todo el cache */
    clear() {
        this.store.clear();
    }
}
