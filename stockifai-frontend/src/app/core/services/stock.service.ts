import { Injectable } from '@angular/core';
import { Movimiento } from '../models/movimiento';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class StockService {
    constructor(private restService: RestService) {}

    getMovimientos(): Promise<Movimiento[]> {
        return this.restService.get<Movimiento[]>('movimientos');
    }

    importarMovimientos(tallerId: number, file: File, fecha?: string): Promise<any> {
        const formData = new FormData();
        formData.append('taller_id', String(tallerId));
        formData.append('file', file);
        if (fecha) {
            formData.append('defaultFecha', fecha);
        }

        return this.restService.upload('importaciones/movimientos', formData);
    }
}
