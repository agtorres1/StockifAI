import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class DepositosService {
    constructor(private restService: RestService) {}

    getDepositosPorGrupo(grupoId: number): Observable<any> {
        return this.restService.get<any>(`grupos/${grupoId}/depositos`);
    }

    getDepositosPorTaller(tallerId: number): Observable<any> {
        return this.restService.get<any>(`talleres/${tallerId}/depositos`);
    }
}
