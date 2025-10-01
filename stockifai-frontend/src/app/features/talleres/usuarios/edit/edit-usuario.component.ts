import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { NgForm } from '@angular/forms';
import { firstValueFrom, forkJoin } from 'rxjs';
import { Grupo } from '../../../../core/models/grupo';
import { Taller } from '../../../../core/models/taller';
import { Usuario } from '../../../../core/models/usuario';
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

    constructor(private usuariosService: UsuariosService, private talleresService: TalleresService) {}

    ngOnInit(): void {
        this.loadingTalleres = true;
        forkJoin([this.usuariosService.getGrupos(), this.talleresService.getTalleres()]).subscribe(
            ([grupos, talleres]) => {
                this.grupos = grupos;
                this.talleres = talleres;
                this.loadingTalleres = false;
            }
        );
    }

    ngOnChanges(changes: SimpleChanges): void {
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
        if(this.usuario.taller) this.scopeType = 'taller';
        if(this.usuario.grupo) this.scopeType = 'grupo';
    }

    async submitUsuarioForm(form: NgForm) {
        this.errorMessage = '';

        if (form.invalid || !this.usuario?.username?.trim()) {
            form.control.markAllAsTouched();
            return;
        }

        try {
            this.loading = true;
            if (this.isEdit && this.usuario?.id) {
                await firstValueFrom(this.usuariosService.editarUsuario(this.usuario.id, this.usuario));
            } else {
                await firstValueFrom(this.usuariosService.crearUsuario(this.usuario));
            }
            this.loading = false;
            this.successMessage = `Usuario ${this.isEdit ? 'editado' : 'creado'} correctamente.`;
            setTimeout(() => {
                this.onSubmit.emit();
                form.resetForm();
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
        } else {
            this.usuario.taller = undefined;
        }
    }

    close(refresh: boolean = false) {
        this.onClose.emit(refresh);
    }
}
