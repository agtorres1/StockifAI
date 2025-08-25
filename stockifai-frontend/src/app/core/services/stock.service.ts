import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Movimiento } from '../models/movimiento';
import { PagedResponse } from '../models/paged-response';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class StockService {
    constructor(private restService: RestService) {}

    getMovimientos(
        tallerId: number,
        page = 1,
        pageSize = 10,
        filtro?: { idDeposito: string; searchText: string, desde?: string, hasta?: string }
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
}
