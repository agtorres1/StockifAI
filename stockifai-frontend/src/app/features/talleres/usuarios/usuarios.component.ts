import { Component, OnInit , ChangeDetectorRef} from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Usuario } from '../../../core/models/usuario';
import { TitleService } from '../../../core/services/title.service';
import { UsuariosService } from '../../../core/services/usuarios.service';
declare const bootstrap: any;
import { AuthService } from '../../../core/services/auth.service';


@Component({
    selector: 'app-usuarios',
    templateUrl: './usuarios.component.html',
    styleUrl: './usuarios.component.scss',
})
export class TalleresUsuariosComponent implements OnInit {
    usuarios: Usuario[] = [];
    loading: boolean = false;
    errorMessage: string = '';
    isSuperUser = false;
    puedeCrearUsuarios=false;

    private modalRef: any | null = null;
    selectedUser: any | null = null;
    isEditMode: boolean = false;

    private deleteModalRef: any | null = null;
    deleting = false;
    deleteErrorMessage = '';

    constructor(
    private titleService: TitleService,
    private usuariosService: UsuariosService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef
    ) {
    this.titleService.setTitle('Usuarios');
    }

    ngOnInit() {
        this.loadUsuarios();
        this.checkIfSuperUser();
    }

    checkIfSuperUser() {
        const currentUser = this.authService.getCurrentUser();


    this.isSuperUser = (currentUser as any)?.is_superuser || false;


    this.puedeCrearUsuarios = this.isSuperUser ||
        ((currentUser as any)?.grupo?.rol === 'admin') ||
        ((currentUser as any)?.taller?.rol === 'owner');

        this.cdr.detectChanges();

}


    async loadUsuarios() {
    this.loading = true;
    console.log('🔍 Cargando usuarios...');

    try {
        const currentUser = this.authService.getCurrentUser();
        const allUsuarios = await firstValueFrom(this.usuariosService.getUsuarios());

        // Filtrar según rol
        if (this.isSuperUser) {
            // Superuser ve TODOS
            this.usuarios = allUsuarios;
        } else if ((currentUser as any)?.grupo?.rol === 'admin') {
            // Admin de grupo ve usuarios de su grupo
            const miGrupoId = (currentUser as any).grupo.id;
            this.usuarios = allUsuarios.filter(u =>
                u.grupo?.id_grupo === miGrupoId
            );
        } else if ((currentUser as any)?.taller?.rol === 'owner') {
    // Owner de taller ve usuarios de su taller
    const miTallerId = (currentUser as any).taller.id;
    console.log('🔍 Mi taller ID:', miTallerId);
    console.log('🔍 Todos los usuarios:', allUsuarios);

    this.usuarios = allUsuarios.filter(u => {
        console.log('Usuario:', u.username, '- Taller ID:', u.taller?.id);
        return u.taller?.id === miTallerId;
    });

    console.log('🔍 Usuarios filtrados:', this.usuarios);
        } else {
            // Member solo se ve a sí mismo
            this.usuarios = allUsuarios.filter(u => u.id === (currentUser as any)?.user_id);
        }

        this.loading = false;
        this.errorMessage = '';
    } catch (error: any) {
        console.error('❌ Error al cargar usuarios:', error);
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
