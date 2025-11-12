import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Grupo } from '../models/grupo';
import { Usuario } from '../models/usuario';
import { RestService } from './rest.service';

@Injectable({ providedIn: 'root' })
export class UsuariosService {
    constructor(private restService: RestService) {}

    getUsuarios(): Observable<Usuario[]> {
        return this.restService.get<Usuario[]>(`usuarios/`);
    }

    crearUsuario(usuario: Usuario): Observable<Usuario> {
        return this.restService.post<Usuario>(`register/`, usuario);
    }
    getUsuario(id: number): Observable<Usuario> {
        return this.restService.get<Usuario>(`usuarios/${id}/`);
    }

    editarUsuario(usuarioId: number, usuario: Usuario): Observable<Usuario> {
        return this.restService.put<Usuario>(`usuarios/${usuarioId}/`, usuario);
    }

    eliminarUsuario(usuarioId: number): Observable<any> {
        return this.restService.delete<any>(`usuarios/${usuarioId}/`);
    }

    getGrupos(): Observable<Grupo[]> {
        return this.restService.get<Grupo[]>(`grupos/`);
    }
}
