import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { NgForm } from '@angular/forms';
import { firstValueFrom, forkJoin } from 'rxjs';
import { Grupo } from '../../../../core/models/grupo';
import { Taller } from '../../../../core/models/taller';
import { Usuario } from '../../../../core/models/usuario';
import { TalleresService } from '../../../../core/services/talleres.service';
import { UsuariosService } from '../../../../core/services/usuarios.service';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
    selector: 'app-edit-usuarios',
    templateUrl: './edit-usuario.component.html',
    styleUrl: './edit-usuario.component.scss',
})
export class EditUsuarioComponent implements OnChanges, OnInit {
    @Input() isEdit: boolean = false;
    @Input() usuario!: Usuario;

    @Output() onSubmit = new EventEmitter<any>();
    @Output() onClose = new EventEmitter<boolean>();

    loading: boolean = false;
    errorMessage: string = '';
    successMessage: string = '';

    scopeType: 'taller' | 'grupo' = 'taller';
    talleres: Taller[] = [];
    grupos: Grupo[] = [];
    loadingTalleres: boolean = false;

    isSuperUser: boolean = false;
    passwordField: string = '';

    constructor(
        private usuariosService: UsuariosService,
        private talleresService: TalleresService,
        private authService: AuthService
    ) {}

    ngOnInit(): void {
    const currentUser = this.authService.getCurrentUser();
    console.log('🔍 DEBUG - Usuario actual:', currentUser);
    console.log('🔍 DEBUG - Es superuser?:', (currentUser as any)?.is_superuser);
    console.log('🔍 DEBUG - Taller:', (currentUser as any)?.taller);
    console.log('🔍 DEBUG - Grupo:', (currentUser as any)?.grupo);
    console.log('🔍 DEBUG - Grupo.id:', (currentUser as any)?.grupo?.id);
    console.log('🔍 DEBUG - isEdit?:', this.isEdit);

    this.isSuperUser = (currentUser as any)?.is_superuser || false;

    this.loadingTalleres = true;
    forkJoin([this.usuariosService.getGrupos(), this.talleresService.getTalleres()]).subscribe(
        ([grupos, talleres]) => {
            this.grupos = grupos;
            this.talleres = talleres;
            this.loadingTalleres = false;
        }
    );

    if (this.isEdit && this.usuario?.id) {
        this.loadUsuarioCompleto(this.usuario.id);
    }

    console.log('🔍 ANTES - usuario:', this.usuario);
    console.log('🔍 ANTES - usuario.id_grupo:', this.usuario?.id_grupo);

    if (!this.isEdit && !this.isSuperUser && currentUser) {
        console.log('🎯 Intentando auto-asignar taller/grupo...');

        if ((currentUser as any).taller) {
            console.log('✅ Asignando taller ID:', (currentUser as any).taller.id);
            this.scopeType = 'taller';
            this.usuario.id_taller = (currentUser as any).taller.id;
            this.usuario.rol_en_taller = 'member';
            console.log('✅ DESPUÉS - usuario.id_taller:', this.usuario.id_taller);
        } else if ((currentUser as any).grupo) {
            console.log('✅ Asignando grupo ID:', (currentUser as any).grupo.id);
            this.scopeType = 'grupo';
            this.usuario.id_grupo = (currentUser as any).grupo.id;
            this.usuario.rol_en_grupo = 'member';
            console.log('✅ DESPUÉS - usuario.id_grupo:', this.usuario.id_grupo);
        } else {
            console.log('❌ Usuario no tiene ni taller ni grupo');
        }
    } else {
        console.log('⚠️ No se auto-asigna porque:', {
            isEdit: this.isEdit,
            isSuperUser: this.isSuperUser,
            hasCurrentUser: !!currentUser
        });
    }

    console.log('🔍 FINAL - usuario.id_grupo:', this.usuario?.id_grupo);
    console.log('🔍 FINAL - usuario completo:', this.usuario);
}

    ngOnChanges(changes: SimpleChanges): void {
    if (!this.isEdit) {
        // Inicializamos el objeto vacío
        this.usuario = {
            username: '',
            email: '',
            first_name: '',
            last_name: '',
            telefono: '',
        };
    }

    // Siempre tener dirección inicial
    this.usuario.direccion = { pais: 'Argentina' };

    // Si estamos editando, cargamos los datos completos
    if (changes['usuario'] && this.isEdit && this.usuario?.id) {
        this.loadUsuarioCompleto(this.usuario.id);
    }

    // 🚀 Asignación automática del grupo/taller
    const currentUser = this.authService.getCurrentUser();
    if (!this.isEdit && currentUser && !this.isSuperUser) {
        if (currentUser.taller) {
            this.scopeType = 'taller';
            this.usuario.id_taller = currentUser.taller.id;
            this.usuario.rol_en_taller = 'member';
            console.log('✅ Asignado taller ID:', currentUser.taller.id);
        } else if (currentUser.grupo) {
            this.scopeType = 'grupo';
            this.usuario.id_grupo = currentUser.grupo.id;
            this.usuario.rol_en_grupo = 'member';
            console.log('✅ Asignado grupo ID:', currentUser.grupo.id);
        } else {
            console.log('⚠️ El usuario actual no tiene ni taller ni grupo');
        }
    }

    // Mantenemos la detección del scope actual
    if (this.usuario?.taller) this.scopeType = 'taller';
    if (this.usuario?.grupo) this.scopeType = 'grupo';

    console.log('🔍 FINAL - usuario.id_grupo:', this.usuario?.id_grupo);
    console.log('🔍 FINAL - usuario completo:', this.usuario);
}


    loadUsuarioCompleto(userId: number) {
        this.loading = true;
        this.usuariosService.getUsuario(userId).subscribe({
            next: (usuarioCompleto: Usuario) => {
                this.usuario = usuarioCompleto;
                if (!this.usuario.direccion) {
                    this.usuario.direccion = { pais: 'Argentina' };
                }
                if (this.usuario.taller) this.scopeType = 'taller';
                if (this.usuario.grupo) this.scopeType = 'grupo';

                this.loading = false;
            },
            error: (error: any) => {
                this.errorMessage = 'Error al cargar los datos del usuario';
                this.loading = false;
            }
        });
    }

    async submitUsuarioForm(form: NgForm) {
        this.errorMessage = '';

        if (form.invalid || !this.usuario?.username?.trim()) {
            form.control.markAllAsTouched();
            return;
        }

        if (!this.isEdit && !this.passwordField?.trim()) {
            this.errorMessage = 'La contraseña es requerida al crear un usuario.';
            return;
        }

        if (this.usuario.direccion) {
            this.usuario.direccion.pais = 'Argentina';
        }

        const usuarioData = {
            ...this.usuario,
            ...(this.passwordField && { password: this.passwordField })
        };

        console.log('📤 Datos a enviar:', usuarioData);
        console.log('📤 id_grupo:', usuarioData.id_grupo);  // ← Y ESTO
        console.log('📤 rol_en_grupo:', usuarioData.rol_en_grupo);  // ← Y ESTO

        try {
            this.loading = true;
            if (this.isEdit && this.usuario?.id) {
                await firstValueFrom(this.usuariosService.editarUsuario(this.usuario.id, usuarioData));
            } else {
                await firstValueFrom(this.usuariosService.crearUsuario(usuarioData));
            }
            this.loading = false;
            this.successMessage = `Usuario ${this.isEdit ? 'editado' : 'creado'} correctamente.`;
            setTimeout(() => {
                this.onSubmit.emit();
                form.resetForm();
                this.passwordField = '';
                this.successMessage = '';
            }, 1500);
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'Error al crear usuario';
            this.loading = false;
        }
    }

    onScopeChange(next: 'taller' | 'grupo') {
        this.scopeType = next;
        if (next === 'taller') {
            this.usuario.grupo = undefined;
            this.usuario.id_grupo = undefined;
            this.usuario.rol_en_grupo = undefined;
        } else {
            this.usuario.taller = undefined;
            this.usuario.id_taller = undefined;
            this.usuario.rol_en_taller = undefined;
        }
    }

    close(refresh: boolean = false) {
        this.onClose.emit(refresh);
    }
}
