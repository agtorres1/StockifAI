import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Categoria } from '../models/categoria';
import { Marca } from '../models/marca';
import { PagedResponse } from '../models/paged-response';
import { Repuesto } from '../models/repuesto';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class RepuestosService {
    constructor(private restService: RestService) {}

    getMarcas(): Observable<Marca[]> {
        return this.restService.get<Marca[]>(`marcas`);
    }

    getCategorias(): Observable<Categoria[]> {
        return this.restService.get<Categoria[]>(`categorias`);
    }

    getRepuestos(
        page = 1,
        pageSize = 10,
        filtro?: { searchText: string; idMarca: string; idCategoria: string }
    ): Observable<PagedResponse<Repuesto>> {
        let params = new HttpParams().set('page', page).set('page_size', pageSize);

        if (filtro?.idMarca) params = params.set('marca_id', filtro.idMarca);
        if (filtro?.idCategoria) params = params.set('categoria_id', filtro.idCategoria);
        if (filtro?.searchText) params = params.set('search_text', filtro.searchText);

        return this.restService.get<PagedResponse<Repuesto>>(`repuestos`, params);
    }

    importarRepuestos(file: File): Observable<any> {
        const formData = new FormData();
        formData.append('file', file);

        return this.restService.upload('importaciones/catalogo', formData);
    }

    importarPrecios(tallerId: number, file: File): Observable<any> {
        const formData = new FormData();
        formData.append('taller_id', String(tallerId));
        formData.append('file', file);

        return this.restService.upload('importaciones/precios', formData);
    }
}
