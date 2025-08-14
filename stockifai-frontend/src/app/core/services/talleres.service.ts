import { Injectable } from '@angular/core';
import { Movimiento } from '../models/movimiento';
import { RestService } from './rest.service';
import { Deposito } from '../models/deposito';

@Injectable({ providedIn: 'root' })
export class TalleresService {
    constructor(private restService: RestService) {}

    getDepositos(tallerId: number): Promise<Deposito[]> {
        return this.restService.get<Deposito[]>(`talleres/${tallerId}/depositos`);
    }
}
