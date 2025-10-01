import { Component, OnInit } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Usuario } from '../../../core/models/usuario';
import { TitleService } from '../../../core/services/title.service';
import { UsuariosService } from '../../../core/services/usuarios.service';
declare const bootstrap: any;

@Component({
    selector: 'app-usuarios',
    templateUrl: './usuarios.component.html',
    styleUrl: './usuarios.component.scss',
})
export class TalleresUsuariosComponent implements OnInit {
    usuarios: Usuario[] = [];
    loading: boolean = false;
    errorMessage: string = '';

    private modalRef: any | null = null;
    selectedUser: any | null = null;
    isEditMode: boolean = false;

    private deleteModalRef: any | null = null;
    deleting = false;
    deleteErrorMessage = '';

    constructor(private titleService: TitleService, private usuariosService: UsuariosService) {
        this.titleService.setTitle('Usuarios');
    }

    ngOnInit() {
        this.loadUsuarios();
    }

    async loadUsuarios() {
        this.loading = true;
        try {
            const res = await firstValueFrom(this.usuariosService.getUsuarios());
            this.usuarios = res;
            this.loading = false;
            this.errorMessage = '';
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'Error al cargar';
            this.loading = false;
        }
    }

    openCrearUsuarioDialog() {
        this.selectedUser = undefined as any;
        this.isEditMode = false;
        this.openModal();
    }

    onEditUsuarioClick(usuario: Usuario) {
        if(usuario.taller) usuario.id_taller = usuario.taller.id;
        if(usuario.grupo) usuario.id_grupo = usuario.grupo.id_grupo;
        this.selectedUser = Object.assign({}, usuario);
        console.log("edit usuario", usuario);
        this.isEditMode = true;
        this.openModal();
    }

    onDeleteUsuarioClick(usuario: Usuario) {
        this.selectedUser = usuario;
        this.deleteErrorMessage = '';
        const el = document.getElementById('deleteUsuarioModal');
        this.deleteModalRef = bootstrap.Modal.getOrCreateInstance(el, { backdrop: 'static', keyboard: false });
        this.deleteModalRef.show();
    }

    onUsuarioUpdated() {
        this.loadUsuarios();
        this.closeModal();
    }

    async deleteUsuario() {
        if (!this.selectedUser) return;

        this.deleteErrorMessage = '';

        try {
            this.deleting = true;
            const res = await firstValueFrom(this.usuariosService.eliminarUsuario(this.selectedUser.id));
            this.deleting = false;
            this.selectedUser = null;
            this.loadUsuarios();
            this.deleteModalRef?.hide();
        } catch (error: any) {
            this.deleteErrorMessage = error?.message ?? 'Error al eliminar usuario';
            this.deleting = false;
        }
    }

    private openModal() {
        const el = document.getElementById('userModal');
        if (!el) return;
        this.modalRef = bootstrap.Modal.getOrCreateInstance(el, { backdrop: 'static', keyboard: false });
        this.modalRef.show();
    }

    closeModal() {
        this.modalRef?.hide();
    }
}
