// src/app/core/services/grupos.service.ts
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { RestService } from './rest.service';


export interface Taller {
    id: number;
    nombre: string;
}

export interface Grupo {
    id_grupo: number;
    nombre: string;
    descripcion: string;
    grupo_padre?: number;
    talleres?: Taller[];
}

@Injectable({ providedIn: 'root' })
export class GruposService {

    constructor(private restService: RestService) {}

    getGrupos(): Observable<Grupo[]> {
        return this.restService.get<Grupo[]>('grupos/');
    }

    getGrupo(id: number): Observable<Grupo> {
        return this.restService.get<Grupo>(`grupos/${id}/`);
    }

    crearGrupo(grupo: Partial<Grupo>): Observable<Grupo> {
        return this.restService.post<Grupo>('grupos/', grupo);
    }

    editarGrupo(id: number, grupo: Partial<Grupo>): Observable<Grupo> {
        return this.restService.put<Grupo>(`grupos/${id}/`, grupo);
    }

    eliminarGrupo(id: number): Observable<void> {
        return this.restService.delete<void>(`grupos/${id}/`);
    }

    // ← AGREGAR ESTOS MÉTODOS
    asignarTaller(grupoId: number, tallerId: number): Observable<any> {
        return this.restService.post(`grupos/${grupoId}/asignar_taller/`, {
            taller_id: tallerId
        });
    }

    desasignarTaller(grupoId: number, tallerId: number): Observable<any> {
        return this.restService.post(`grupos/${grupoId}/desasignar_taller/`, {
            taller_id: tallerId
        });
    }
}
