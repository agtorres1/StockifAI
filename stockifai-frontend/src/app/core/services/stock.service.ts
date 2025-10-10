import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, Observable, shareReplay, throwError } from 'rxjs';
import { ForecastResponse } from '../models/forecast-response';
import { Movimiento } from '../models/movimiento';
import { PagedResponse } from '../models/paged-response';
import { RepuestoStock } from '../models/repuesto-stock';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class StockService {
    constructor(private restService: RestService) {}

    getMovimientos(
        tallerId: number,
        page = 1,
        pageSize = 10,
        filtro?: { idDeposito: string; searchText: string; desde?: string; hasta?: string }
    ): Observable<PagedResponse<Movimiento>> {
        let params = new HttpParams().set('page', page).set('page_size', pageSize);

        if (filtro?.idDeposito) params = params.set('deposito_id', filtro.idDeposito);
        if (filtro?.searchText) params = params.set('search_text', filtro.searchText);
        if (filtro?.desde) params = params.set('date_from', filtro.desde);
        if (filtro?.hasta) params = params.set('date_to', filtro.hasta);

        return this.restService.get<PagedResponse<Movimiento>>(`talleres/${tallerId}/movimientos`, params);
    }

    importarMovimientos(tallerId: number, file: File, fecha?: string): Observable<any> {
        const formData = new FormData();
        formData.append('taller_id', String(tallerId));
        formData.append('file', file);
        if (fecha) {
            formData.append('defaultFecha', fecha);
        }

        return this.restService.upload('importaciones/movimientos', formData);
    }

    importarStockInicial(tallerId: number, file: File): Observable<any> {
        const formData = new FormData();
        formData.append('taller_id', String(tallerId));
        formData.append('file', file);

        return this.restService.upload('importaciones/stock', formData);
    }

    getStock(
        tallerId: number,
        page = 1,
        pageSize = 10,
        filtro?: { searchText: string; idCategoria?: string }
    ): Observable<PagedResponse<RepuestoStock>> {
        let params = new HttpParams().set('page', page).set('page_size', pageSize);

        if (filtro?.searchText) params = params.set('q', filtro.searchText);
        if (filtro?.idCategoria) params = params.set('categoria_id', filtro.idCategoria);

        return this.restService.get<PagedResponse<RepuestoStock>>(`talleres/${tallerId}/stock`, params);
    }

    getForecastingList(
        tallerId: number,
        page = 1,
        pageSize = 10,
        filtro?: { searchText: string }
    ): Observable<PagedResponse<RepuestoStock>> {
        let params = new HttpParams().set('page', page).set('page_size', pageSize);

        if (filtro?.searchText) params = params.set('q', filtro.searchText);

        return this.restService.get<PagedResponse<RepuestoStock>>(`talleres/${tallerId}/forecasting`, params);
    }

    private cache = new Map<string, { obs$: Observable<ForecastResponse>; exp: number }>();
    private TTL = 60_000; // 1 minuto (ajustá a gusto)

    getRepuestoTallerForecast(tallerId: number, repuestoTallerId: number): Observable<ForecastResponse> {
        const url = `talleres/${tallerId}/repuestos/${repuestoTallerId}/forecasting`;

        const now = Date.now();
        const hit = this.cache.get(url);

        if (hit && hit.exp > now) {
            return hit.obs$; // devolver lo cacheado
        }

        const obs$ = this.restService.get<ForecastResponse>(url).pipe(
            shareReplay(1),
            catchError((err) => {
                this.cache.delete(url);
                return throwError(() => err);
            })
        );

        this.cache.set(url, { obs$, exp: now + this.TTL });
        return obs$;

        /*
        return this.restService.get<ForecastResponse>(
            `talleres/${tallerId}/repuestos/${repuestoTallerId}/forecasting`
        );
        */
    }

    procesarRepuestoStock(item: RepuestoStock): RepuestoStock {
        const min = item.repuesto_taller.cantidad_minima;
        if (min != null) {
            item.estaBajoMinimo = item.stock_total < min;
        }

        const repuesto = item.repuesto_taller;
        repuesto.pred_mensual =
            (repuesto.pred_1 ?? 0) + (repuesto.pred_2 ?? 0) + (repuesto.pred_3 ?? 0) + (repuesto.pred_4 ?? 0);

        if (repuesto.pred_mensual > 0) {
            repuesto.promedio_pred_mensual = repuesto.pred_mensual / 4;
            if (repuesto.pred_1 && repuesto.promedio_pred_mensual > repuesto.pred_1) {
                repuesto.tendencia = 'ALTA';
            } else if (repuesto.pred_1 && repuesto.promedio_pred_mensual < repuesto.pred_1) {
                repuesto.tendencia = 'BAJA';
            } else {
                repuesto.tendencia = 'ESTABLE';
            }
        }

        return item;
    }
}
