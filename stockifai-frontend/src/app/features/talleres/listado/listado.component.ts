import { Component, OnInit } from '@angular/core';
import { NgForm } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Taller } from '../../../core/models/taller';
import { TalleresService } from '../../../core/services/talleres.service';
import { TitleService } from '../../../core/services/title.service';
import { AuthService } from '../../../core/services/auth.service';
declare const bootstrap: any;

@Component({
    selector: 'app-listado',
    templateUrl: './listado.component.html',
    styleUrl: './listado.component.scss',
})

export class TalleresListadoComponent implements OnInit {
    talleres: Taller[] = [];
    loading: boolean = false;
    errorMessage: string = '';
    isSuperUser = false;
    puedeEditarTalleres = false;
    puedeCrearTalleres = false;


    private crearModalRef: any | null = null;
    isEditMode: boolean = false;
    dialogLoading: boolean = false;
    dialogErrorMessage: string = '';
    dialogSuccessMessage: string = '';
    nuevoTaller: Taller = {
        nombre: '',
        direccion: '',
        telefono: '',
        email: '',
        stock_inicial_cargado: false,
        fecha_creacion: new Date().toISOString(),
    };

    private deleteModalRef: any | null = null;
    selectedTaller: any | null = null;
    deleting = false;
    deleteErrorMessage = '';

    constructor(
      private titleService: TitleService,
      private talleresService: TalleresService,
      private authService: AuthService
      ) {
        this.titleService.setTitle('Talleres');

    }

    ngOnInit() {
    const currentUser = this.authService.getCurrentUser();
    this.isSuperUser = (currentUser as any)?.is_superuser || false;

    this.puedeCrearTalleres = this.isSuperUser ||
        ((currentUser as any)?.grupo?.rol === 'admin');

    // Puede editar: superuser, admin de grupo, o owner de su taller
    this.puedeEditarTalleres = this.isSuperUser ||
        ((currentUser as any)?.grupo?.rol === 'admin') ||
        ((currentUser as any)?.taller?.rol === 'owner');

    this.loadTalleres();
}



    async loadTalleres() {
        this.loading = true;
        try {
            const res = await firstValueFrom(this.talleresService.getTalleres());
            this.talleres = res;
            this.loading = false;
            this.errorMessage = '';
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'Error al cargar';
            this.loading = false;
        }
    }

    async submitTallerForm(form: NgForm) {
        this.dialogErrorMessage = '';
        this.dialogSuccessMessage = '';

        if (form.invalid || !this.nuevoTaller.nombre?.trim()) {
            form.control.markAllAsTouched();
            return;
        }

        try {
            this.dialogLoading = true;
            if (this.isEditMode && this.nuevoTaller.id) {
                await firstValueFrom(this.talleresService.editarTaller(this.nuevoTaller.id, this.nuevoTaller));
            } else {
                await firstValueFrom(this.talleresService.crearTaller(this.nuevoTaller));
            }
            this.dialogLoading = false;
            this.dialogSuccessMessage = `Taller ${this.isEditMode ? 'editado' : 'creado'} correctamente.`;
            setTimeout(() => this.closeCrearTallerDialog(true), 1500);
        } catch (error: any) {
            this.dialogErrorMessage = error?.message ?? 'Error al crear taller';
            this.dialogLoading = false;
        }
    }

    openCrearTallerDialog() {
        const el = document.getElementById('crearTallerModal');
        this.crearModalRef = bootstrap.Modal.getOrCreateInstance(el, { backdrop: 'static', keyboard: false });
        this.crearModalRef.show();

        this.dialogErrorMessage = '';
        this.dialogSuccessMessage = '';
    }

    closeCrearTallerDialog(refresh: boolean = false) {
        this.crearModalRef?.hide();
        this.resetCrearForm();
        if (refresh) {
            this.loadTalleres();
        }
    }

    onEditTallerClick(taller: Taller) {
        this.selectedTaller = taller;
        this.isEditMode = true;
        this.nuevoTaller = { ...taller };
        this.dialogErrorMessage = this.dialogSuccessMessage = '';
        this.openCrearTallerDialog();
    }

    onDeleteTallerClick(taller: Taller) {
        this.selectedTaller = taller;
        this.deleteErrorMessage = '';
        const el = document.getElementById('deleteTallerModal');
        this.deleteModalRef = bootstrap.Modal.getOrCreateInstance(el, { backdrop: 'static', keyboard: false });
        this.deleteModalRef.show();
    }

    async deleteTaller() {
        if (!this.selectedTaller) return;

        this.deleteErrorMessage = '';

        try {
            this.deleting = true;
            const res = await firstValueFrom(this.talleresService.eliminarTaller(this.selectedTaller.id));
            this.deleting = false;
            this.selectedTaller = null;
            this.loadTalleres();
            this.deleteModalRef?.hide();
        } catch (error: any) {
            this.deleteErrorMessage = error?.message ?? 'Error al eliminar taller';
            this.deleting = false;
        }
    }

    private resetCrearForm() {
        this.nuevoTaller = {
            nombre: '',
            direccion: '',
            telefono: '',
            email: '',
            fecha_creacion: new Date().toISOString(),
            stock_inicial_cargado: false,
        };
        this.dialogLoading = false;
        this.dialogErrorMessage = '';
        this.dialogSuccessMessage = '';
    }
}
