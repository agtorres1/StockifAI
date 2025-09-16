import { Injectable } from '@angular/core';
import { Deposito } from '../models/deposito';
import { RestService } from './rest.service';
import { Observable } from 'rxjs';
import { Taller } from '../models/taller';

@Injectable({ providedIn: 'root' })
export class TalleresService {
    constructor(private restService: RestService) {}

    getDepositos(tallerId: number): Observable<Deposito[]> {
        return this.restService.get<Deposito[]>(`talleres/${tallerId}/depositos`);
    }

    getTallerData(tallerId: number): Observable<Taller> {
        return this.restService.get<Taller>(`talleres/${tallerId}`);
    }
}
