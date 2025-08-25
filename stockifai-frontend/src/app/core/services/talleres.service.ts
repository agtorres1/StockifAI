import { Injectable } from '@angular/core';
import { Deposito } from '../models/deposito';
import { RestService } from './rest.service';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class TalleresService {
    constructor(private restService: RestService) {}

    getDepositos(tallerId: number): Observable<Deposito[]> {
        return this.restService.get<Deposito[]>(`talleres/${tallerId}/depositos`);
    }
}
