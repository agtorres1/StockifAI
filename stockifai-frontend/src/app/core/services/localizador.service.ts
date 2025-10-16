import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { LocalizadorRespuesta, LocalizadorTaller } from '../models/localizador';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class LocalizadorService {
    constructor(private restService: RestService) {}

    buscarPorNumeroParte(tallerId: number, numeroPieza: string): Observable<LocalizadorRespuesta> {
        const params = new HttpParams().set('numero_pieza', numeroPieza.trim());

        return this.restService.get<any>(`talleres/${tallerId}/localizador`, params).pipe(
            map((response) => this.mapRespuesta(response))
        );
    }

    private mapRespuesta(response: any): LocalizadorRespuesta {
        const talleres: LocalizadorTaller[] = (response?.talleres ?? []).map((t: any) => ({
            id: t.id,
            nombre: t.nombre,
            direccion: t.direccion ?? '',
            direccionNormalizada: t.direccion_normalizada ?? undefined,
            telefono: t.telefono ?? undefined,
            telefonoE164: t.telefono_e164 ?? undefined,
            email: t.email ?? undefined,
            lat: this.toNullableNumber(t.latitud),
            lng: this.toNullableNumber(t.longitud),
            cantidad: Number(t.cantidad ?? 0),
            distanciaKm: this.toNullableNumber(t.distancia_km),
            grupos: (t.grupos ?? []).map((g: any) => ({
                id: g.id,
                nombre: g.nombre,
                descripcion: g.descripcion ?? '',
                esSubgrupo: Boolean(g.es_subgrupo),
                grupoPadreId: this.toNullableNumber(g.grupo_padre_id),
            })),
        }));

        return {
            repuesto: {
                id: response?.repuesto?.id ?? 0,
                numero_pieza: response?.repuesto?.numero_pieza ?? '',
                descripcion: response?.repuesto?.descripcion ?? null,
            },
            tallerOrigen: {
                id: response?.taller_origen?.id ?? 0,
                nombre: response?.taller_origen?.nombre ?? '',
                latitud: this.toNullableNumber(response?.taller_origen?.latitud),
                longitud: this.toNullableNumber(response?.taller_origen?.longitud),
            },
            totalCantidad:
                response?.total_cantidad ?? talleres.reduce((acc, item) => acc + (item.cantidad ?? 0), 0),
            talleres,
        };
    }

    private toNullableNumber(value: any): number | null {
        if (value === null || value === undefined || value === '') {
            return null;
        }
        const num = Number(value);
        return Number.isFinite(num) ? num : null;
    }
}
