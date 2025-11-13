import { HttpParams, HttpResponse, HttpClient  } from '@angular/common/http';
import { Injectable } from '@angular/core';
import {
    catchError,
    distinctUntilChanged,
    filter,
    map,
    merge,
    Observable,
    of,
    shareReplay,
    Subject,
    switchMap,
    throwError,
    timer,
} from 'rxjs';
import { Alerta, NivelAlerta } from '../models/alerta';
import { AlertasResumen } from '../models/alertas-resumen';
import { PagedResponse } from '../models/paged-response';
import { TotalesPorCategoria } from '../models/salud-inventario';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class AlertasService {
    INTERVAL_TIMING_MS = 30000;

    private resumenRefresh$ = new Subject<number>();

    constructor(private restService: RestService,
                private http: HttpClient,
                ) {}

    summary$(tallerId: number): Observable<AlertasResumen> {
        return merge(
            timer(0, this.INTERVAL_TIMING_MS),
            this.resumenRefresh$.pipe(filter((id) => id === tallerId))
        ).pipe(
            switchMap(() => this.getResumenAlertas(tallerId)),
            distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
            shareReplay({ bufferSize: 1, refCount: true })
        );
    }

    getKPIsResumen(tallerId: number): Observable<any> {
    const params = new HttpParams().set('taller_id', tallerId.toString());

    return this.restService.get<any>('kpis/resumen/', params).pipe(
        catchError((error) => {
            if (error.status === 403) {
                return of({
                    tasa_rotacion: { valor: 0, objetivo: 0 },
                    dias_en_mano: { valor: 0, objetivo: 0 },
                    dead_stock: { porcentaje: 0, objetivo: 0 },
                });
            }
            return throwError(() => error);
        })
    );
}


    getAlertas(
        tallerId: number,
        niveles: NivelAlerta[],
        page: number = 1,
        pageSize: number = 50
    ): Observable<PagedResponse<Alerta>> {
        const params = new HttpParams().set('niveles', niveles.join(',')).set('page', page).set('page_size', pageSize);

        return this.restService.get<PagedResponse<Alerta>>(`talleres/${tallerId}/alertas/`, params).pipe(
            catchError((error) => {
                if (error.status === 403) {
                    // Usuario sin acceso al taller - retorna respuesta vacía
                    return of({
                        count: 0,
                        next: null,
                        previous: null,
                        results: [],
                        page: page, // ← AGREGADO
                        page_size: pageSize, // ← AGREGADO
                        total_pages: 0, // ← AGREGADO
                    } as PagedResponse<Alerta>);
                }
                // Re-lanza otros errores para que el componente los maneje
                return throwError(() => error);
            })
        );
    }

    getAlertasPorRepuesto(
        tallerId: number,
        repuestoTallerId: number,
        niveles: NivelAlerta[],
        page: number = 1,
        pageSize: number = 50
    ): Observable<PagedResponse<Alerta>> {
        const params = new HttpParams().set('niveles', niveles.join(',')).set('page', page).set('page_size', pageSize);

        return this.restService
            .get<PagedResponse<Alerta>>(`talleres/${tallerId}/repuestos/${repuestoTallerId}/alertas/`, params)
            .pipe(
                catchError((error) => {
                    if (error.status === 403) {
                        return of({
                            count: 0,
                            next: null,
                            previous: null,
                            results: [],
                            page: page, // ← AGREGADO
                            page_size: pageSize, // ← AGREGADO
                            total_pages: 0, // ← AGREGADO
                        } as PagedResponse<Alerta>);
                    }
                    return throwError(() => error);
                })
            );
    }

    dismissAlerta(alertaId: number) {
        return this.restService.post<void>(`alertas/${alertaId}/dismiss/`, {});
    }

    markAsSeenAlerta(alertaId: number) {
        return this.restService.post<void>(`alertas/${alertaId}/mark-as-seen/`, {});
    }

    triggerResumenRefresh(tallerId: number) {
        this.resumenRefresh$.next(tallerId);
    }

    exportarListadoComprarUrgentes(tallerId: number): Observable<HttpResponse<Blob>> {
        return this.restService.getBlobResponse(`talleres/${tallerId}/exportar-urgentes/`);
    }

    exportarReporteSaludInventario(tallerId: number): Observable<HttpResponse<Blob>> {
        return this.restService.getBlobResponse(`talleres/${tallerId}/salud-inventario/exportar/`);
    }

    getSaludInventario(tallerId: number): Observable<TotalesPorCategoria[]> {
        return this.restService.get<TotalesPorCategoria[]>(`talleres/${tallerId}/salud-por-categoria/`).pipe(
            catchError((error) => {
                if (error.status === 403) {
                    return of([] as TotalesPorCategoria[]);
                }
                return throwError(() => error);
            })
        );
    }

    private getResumenAlertas(tallerId: number): Observable<AlertasResumen> {
        const url = `talleres/${tallerId}/alertas/`;
        let params = new HttpParams().set('summary', 1);

        return this.restService.get<any>(url, params).pipe(
            map((res) => ({
                critico: res?.CRITICO ?? 0,
                medio: res?.MEDIO ?? 0,
                advertencia: res?.ADVERTENCIA ?? 0,
                informativo: res?.INFORMATIVO ?? 0,
                totalUrgente: res?.TOTAL_URGENTE ?? 0,
            })),
            catchError((error) => {
                // Para 403 o cualquier error, retorna resumen vacío
                return of({
                    critico: 0,
                    medio: 0,
                    advertencia: 0,
                    informativo: 0,
                    totalUrgente: 0,
                });
            })
        );
    }
}
