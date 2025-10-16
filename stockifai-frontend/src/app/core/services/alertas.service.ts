import { HttpParams } from '@angular/common/http';
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
    timer,
} from 'rxjs';
import { Alerta, NivelAlerta } from '../models/alerta';
import { AlertasResumen } from '../models/alertas-resumen';
import { PagedResponse } from '../models/paged-response';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class AlertasService {
    INTERVAL_TIMING_MS = 60000;

    private resumenRefresh$ = new Subject<number>();

    constructor(private restService: RestService) {}

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

    getAlertas(
        tallerId: number,
        niveles: NivelAlerta[],
        page: number = 1,
        pageSize: number = 50
    ): Observable<PagedResponse<Alerta>> {
        const params = new HttpParams().set('niveles', niveles.join(',')).set('page', page).set('page_size', pageSize);
        return this.restService.get<PagedResponse<Alerta>>(`talleres/${tallerId}/alertas/`, params);
    }

    getAlertasPorRepuesto(
        tallerId: number,
        repuestoTallerId: number,
        niveles: NivelAlerta[],
        page: number = 1,
        pageSize: number = 50
    ): Observable<PagedResponse<Alerta>> {
        const params = new HttpParams().set('niveles', niveles.join(',')).set('page', page).set('page_size', pageSize);

        return this.restService.get<PagedResponse<Alerta>>(`talleres/${tallerId}/repuestos/${repuestoTallerId}/alertas/`, params);
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
            catchError(() => of({ critico: 0, medio: 0, advertencia: 0, informativo: 0, totalUrgente: 0 }))
        );
    }
}
