import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { NgForm } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Usuario } from '../../../../core/models/usuario';
import { UsuariosService } from '../../../../core/services/usuarios.service';

@Component({
    selector: 'app-edit-usuarios',
    templateUrl: './edit-usuario.component.html',
    styleUrl: './edit-usuario.component.scss',
})
export class EditUsuarioComponent implements OnChanges {
    @Input() isEdit: boolean = false;
    @Input() usuario!: Usuario;

    @Output() onSubmit = new EventEmitter<any>();
    @Output() onClose = new EventEmitter<boolean>();

    loading: boolean = false;
    errorMessage: string = '';
    successMessage: string = '';

    constructor(private usuariosService: UsuariosService) {}

    ngOnChanges(changes: SimpleChanges): void {
        console.log("changes", changes);
        if (!this.isEdit) {
            this.usuario = { username: '', email: '', first_name: '', last_name: '', telefono: '', direccion: ''};
        }
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

    close(refresh: boolean = false) {
        this.onClose.emit(refresh);
    }
}
