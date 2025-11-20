import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { ForecastResponse } from '../models/forecast-response';
import { Movimiento } from '../models/movimiento';
import { PagedResponse } from '../models/paged-response';
import { RepuestoStock } from '../models/repuesto-stock';
import { CacheService } from './cache.service';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class StockService {
    constructor(private restService: RestService, private cacheService: CacheService) {}

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

        if (filtro?.searchText) {
            params = params.set('q', filtro.searchText);
        }

        if (filtro?.idCategoria) {
            params = params.set('categoria_id', filtro.idCategoria);
        }

        const key = `stock-${tallerId}-${page}-${pageSize}-${filtro?.searchText ?? ''}-${filtro?.idCategoria ?? ''}`;
        const cached = this.cacheService.get<PagedResponse<RepuestoStock>>(key);
        if (cached) return cached;

        return this.restService
            .get<PagedResponse<RepuestoStock>>(`talleres/${tallerId}/stock`, params)
            .pipe(tap((resp) => this.cacheService.set(key, resp)));
    }

    getForecastingList(
        tallerId: number,
        page = 1,
        pageSize = 10,
        filtro?: { searchText: string }
    ): Observable<PagedResponse<RepuestoStock>> {
        const cacheKey = `forecasting-${tallerId}-${page}-${pageSize}-${filtro?.searchText ?? ''}`;
        const cached = this.cacheService.get<PagedResponse<RepuestoStock>>(cacheKey);

        if (cached) return cached;

        let params = new HttpParams().set('page', page).set('page_size', pageSize);

        if (filtro?.searchText) params = params.set('q', filtro.searchText);

        return this.restService
            .get<PagedResponse<RepuestoStock>>(`talleres/${tallerId}/forecasting`, params)
            .pipe(tap((res) => this.cacheService.set(cacheKey, res)));
    }

    getRepuestoTallerForecast(tallerId: number, repuestoTallerId: number): Observable<ForecastResponse> {
        const cacheKey = `forecast-${tallerId}-${repuestoTallerId}`;
        const cached$ = this.cacheService.get<ForecastResponse>(cacheKey);
        if (cached$) return cached$;

        const url = `talleres/${tallerId}/repuestos/${repuestoTallerId}/forecasting`;

        return this.restService
            .get<ForecastResponse>(`talleres/${tallerId}/repuestos/${repuestoTallerId}/forecasting`)
            .pipe(tap((res) => this.cacheService.set(cacheKey, res)));
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
