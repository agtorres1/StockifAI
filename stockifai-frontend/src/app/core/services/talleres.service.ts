import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Deposito } from '../models/deposito';
import { Taller } from '../models/taller';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class TalleresService {
    constructor(private restService: RestService) {}

    getDepositos(tallerId: number): Observable<Deposito[]> {
        return this.restService.get<Deposito[]>(`talleres/${tallerId}/depositos`);
    }

    getTallerData(tallerId: number): Observable<Taller> {
        return this.restService.get<Taller>(`taller-data/${tallerId}`);
    }

    getTalleres(): Observable<Taller[]> {
        return this.restService.get<Taller[]>(`talleres/`);
    }

    crearTaller(taller: Taller): Observable<Taller> {
        return this.restService.post<Taller>(`talleres/`, taller);
    }

    editarTaller(tallerId: number, taller: Taller): Observable<Taller> {
        return this.restService.put<Taller>(`talleres/${tallerId}/`, taller);
    }

    eliminarTaller(tallerId: number): Observable<any> {
        return this.restService.delete<any>(`talleres/${tallerId}/`);
    }

    getDepositosPorGrupo(grupoId: number): Observable<any> {
    return this.restService.get<any>(`grupos/${grupoId}/depositos`);
    }

    getGrupoData(grupoId: number): Observable<any> {
        return this.restService.get<any>(`grupos/${grupoId}/`);
    }
}
