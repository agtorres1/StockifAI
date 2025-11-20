import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { NgForm } from '@angular/forms';
import { firstValueFrom, forkJoin } from 'rxjs';
import { Grupo } from '../../../../core/models/grupo';
import { Taller } from '../../../../core/models/taller';
import { Usuario } from '../../../../core/models/usuario';
import { AuthService } from '../../../../core/services/auth.service';
import { TalleresService } from '../../../../core/services/talleres.service';
import { UsuariosService } from '../../../../core/services/usuarios.service';

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
    puedeEditarScope: boolean = false;

    isSuperUser: boolean = false;
    puedeAsignarUsuarios: boolean = false;
    passwordField: string = '';

    constructor(
        private usuariosService: UsuariosService,
        private talleresService: TalleresService,
        private authService: AuthService
    ) {}

    ngOnInit(): void {
        const currentUser = this.authService.getCurrentUser();

        this.isSuperUser = (currentUser as any)?.is_superuser || false;
        this.puedeAsignarUsuarios =
            this.isSuperUser ||
            (currentUser as any)?.grupo?.rol === 'admin' ||
            (currentUser as any)?.taller?.rol === 'owner';

        this.puedeEditarScope = this.isSuperUser;

        this.loadingTalleres = true;

        // Si es superuser, carga TODO
        if (this.isSuperUser) {
            forkJoin([this.usuariosService.getGrupos(), this.talleresService.getTalleres()]).subscribe(
                ([grupos, talleres]) => {
                    this.grupos = grupos;
                    this.talleres = talleres;
                    this.loadingTalleres = false;
                }
            );
        }
        // Si es admin de grupo, solo carga su grupo y talleres de su grupo
        else if ((currentUser as any)?.grupo) {
            const grupoId = (currentUser as any).grupo.id_grupo;

            forkJoin([this.usuariosService.getGrupos(), this.talleresService.getTalleres()]).subscribe(
                ([grupos, allTalleres]) => {
                    // Solo su grupo
                    this.grupos = grupos.filter((g) => g.id_grupo === grupoId);

                    // Solo talleres de su grupo
                    const miGrupo: any = grupos.find((g) => g.id_grupo === grupoId);
                    if (miGrupo && miGrupo.talleres) {
                        const talleresIds = miGrupo.talleres.map((t: any) => t.id);
                        this.talleres = allTalleres.filter((t) => talleresIds.includes(t.id));
                    } else {
                        this.talleres = [];
                    }

                    this.loadingTalleres = false;
                }
            );
        } else if ((currentUser as any)?.taller) {
            this.talleresService.getTalleres().subscribe((allTalleres) => {
                const tallerId = (currentUser as any).taller.id;
                this.talleres = allTalleres.filter((t) => t.id === tallerId);
                this.grupos = [];

                this.loadingTalleres = false;
            });
        } else {
            this.loadingTalleres = false;
        }

        if (this.isEdit && this.usuario?.id) {
            this.loadUsuarioCompleto(this.usuario.id);
        }

        if (!this.isEdit && !this.isSuperUser && currentUser) {
            if ((currentUser as any).taller) {
                this.scopeType = 'taller';
                this.usuario.id_taller = (currentUser as any).taller.id;
                this.usuario.rol_en_taller = 'member';
            } else if ((currentUser as any).grupo) {
                this.scopeType = 'grupo';
                this.usuario.id_grupo = (currentUser as any).grupo.id_grupo;
                this.usuario.rol_en_grupo = 'member';
            }
        } else {
            console.log('⚠️ No se auto-asigna porque:', {
                isEdit: this.isEdit,
                isSuperUser: this.isSuperUser,
                hasCurrentUser: !!currentUser,
            });
        }
    }

    ngOnChanges(changes: SimpleChanges): void {
        const currentUser = this.authService.getCurrentUser();

        this.isSuperUser = (currentUser as any)?.is_superuser || false;
        this.puedeAsignarUsuarios =
            this.isSuperUser ||
            (currentUser as any)?.grupo?.rol === 'admin' ||
            (currentUser as any)?.taller?.rol === 'owner';

        // ✅ CARGAR TALLERES Y GRUPOS
        if (!this.loadingTalleres) {
            this.loadingTalleres = true;

            if (this.isSuperUser) {
                forkJoin([this.usuariosService.getGrupos(), this.talleresService.getTalleres()]).subscribe(
                    ([grupos, talleres]) => {
                        this.grupos = grupos;
                        this.talleres = talleres;
                        this.loadingTalleres = false;
                    }
                );
            } else if ((currentUser as any)?.grupo) {
                const grupoId = (currentUser as any).grupo.id_grupo; // ← CORREGIDO

                forkJoin([this.usuariosService.getGrupos(), this.talleresService.getTalleres()]).subscribe(
                    ([grupos, allTalleres]) => {
                        this.grupos = grupos.filter((g) => g.id_grupo === grupoId);

                        const miGrupo: any = grupos.find((g) => g.id_grupo === grupoId);
                        if (miGrupo && miGrupo.talleres) {
                            const talleresIds = miGrupo.talleres.map((t: any) => t.id);
                            this.talleres = allTalleres.filter((t) => talleresIds.includes(t.id));
                        } else {
                            this.talleres = [];
                        }

                        this.loadingTalleres = false;
                    }
                );
            } else if ((currentUser as any)?.taller) {
                this.talleresService.getTalleres().subscribe((allTalleres) => {
                    const tallerId = (currentUser as any).taller.id;
                    this.talleres = allTalleres.filter((t) => t.id === tallerId);
                    this.grupos = [];

                    this.loadingTalleres = false;
                });
            } else {
                this.loadingTalleres = false;
            }
        }

        if (!this.isEdit) {
            this.usuario = {
                username: '',
                email: '',
                first_name: '',
                last_name: '',
                telefono: '',
            };
        }

        this.usuario.direccion = { pais: 'Argentina' };

        if (changes['usuario'] && this.isEdit && this.usuario?.id) {
            this.loadUsuarioCompleto(this.usuario.id);
        }

        if (!this.isEdit && currentUser && !this.isSuperUser) {
            if (currentUser.taller) {
                this.scopeType = 'taller';
                this.usuario.id_taller = currentUser.taller.id;
                this.usuario.rol_en_taller = 'member';
            } else if (currentUser.grupo) {
                this.scopeType = 'grupo';
                this.usuario.id_grupo = currentUser.grupo.id_grupo;
                this.usuario.rol_en_grupo = 'member';
            }
        }

        if (this.usuario?.taller) this.scopeType = 'taller';
        if (this.usuario?.grupo) this.scopeType = 'grupo';
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
            },
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
            ...(this.passwordField && { password: this.passwordField }),
        };

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
