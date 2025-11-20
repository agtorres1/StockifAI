import { Component, OnInit } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { TitleService } from '../../../core/services/title.service';
import { GruposService, Grupo, Taller } from '../../../core/services/grupos.service';
import { TalleresService } from '../../../core/services/talleres.service';  // ← Este import ya está bien
import { AuthService } from '../../../core/services/auth.service';
declare const bootstrap: any;


@Component({
    selector: 'app-grupos',
    templateUrl: './grupos.component.html',
    styleUrl: './grupos.component.scss'
})

export class GruposComponent implements OnInit {

    isSuperUser = false;
    grupos: Grupo[] = [];
    talleres: any[] = []; // Todos los talleres disponibles
    loading = false;
    errorMessage = '';

    // Para modales
    selectedGrupo: Grupo | null = null;
    isEditMode = false;
    grupoForm: Partial<Grupo> = {};

    // Para modal de eliminar
    deleting = false;
    deleteErrorMessage = '';

    // Para modal de talleres
    talleresDisponibles: any[] = [];
    talleresAsignados: number[] = [];
    loadingTalleres = false;

    private modalRef: any = null;
    private deleteModalRef: any = null;
    private talleresModalRef: any = null;

    constructor(
        private titleService: TitleService,
        private gruposService: GruposService,
        private talleresService: TalleresService,  // ← Esto ya funciona con tu servicio
        private authService: AuthService
    ) {
        this.titleService.setTitle('Grupos');
    }

    ngOnInit() {
        this.cargarGrupos();
        this.cargarTalleres();
        const currentUser = this.authService.getCurrentUser();
        this.isSuperUser = (currentUser as any)?.is_superuser || false;
    }

    async cargarGrupos() {
        this.loading = true;

        try {
            this.grupos = await firstValueFrom(this.gruposService.getGrupos());
            this.loading = false;
            this.errorMessage = '';
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'Error al cargar grupos';
            this.loading = false;
        }
    }

    async cargarTalleres() {
        try {
            this.talleres = await firstValueFrom(this.talleresService.getTalleres());
        } catch (error) {
            console.error('Error al cargar talleres:', error);
        }
    }

    crearGrupo() {
        this.isEditMode = false;
        this.grupoForm = {
            nombre: '',
            descripcion: '',
            grupo_padre: undefined
        };
        this.openModal();
    }

    editarGrupo(grupo: Grupo) {
        this.isEditMode = true;
        this.grupoForm = { ...grupo };
        this.openModal();
    }

    async submitGrupo() {
        if (!this.grupoForm.nombre || !this.grupoForm.descripcion) {
            alert('Por favor completa todos los campos obligatorios');
            return;
        }

        try {
            if (this.isEditMode && this.grupoForm.id_grupo) {
                await firstValueFrom(
                    this.gruposService.editarGrupo(this.grupoForm.id_grupo, this.grupoForm)
                );
            } else {
                await firstValueFrom(
                    this.gruposService.crearGrupo(this.grupoForm)
                );
            }

            this.closeModal();
            this.cargarGrupos();
        } catch (error: any) {
            console.error('❌ Error al guardar grupo:', error);
            alert(error?.error?.error || 'Error al guardar el grupo');
        }
    }

    eliminarGrupo(grupo: Grupo) {
        this.selectedGrupo = grupo;
        this.deleteErrorMessage = '';
        this.openDeleteModal();
    }

    async confirmarEliminar() {
        if (!this.selectedGrupo) return;

        this.deleting = true;
        this.deleteErrorMessage = '';

        try {
            await firstValueFrom(
                this.gruposService.eliminarGrupo(this.selectedGrupo.id_grupo)
            );
            this.closeDeleteModal();
            this.cargarGrupos();
        } catch (error: any) {
            console.error('❌ Error al eliminar grupo:', error);
            this.deleteErrorMessage = error?.error?.error || 'Error al eliminar el grupo';
        } finally {
            this.deleting = false;
        }
    }

    // MÉTODOS PARA TALLERES
    gestionarTalleres(grupo: Grupo) {
        this.selectedGrupo = grupo;
        this.talleresAsignados = grupo.talleres?.map(t => t.id) || [];
        this.talleresDisponibles = [...this.talleres];
        this.openTalleresModal();
    }

    toggleTaller(tallerId: number) {
        const index = this.talleresAsignados.indexOf(tallerId);
        if (index > -1) {
            this.talleresAsignados.splice(index, 1);
        } else {
            this.talleresAsignados.push(tallerId);
        }
    }

    isTallerAsignado(tallerId: number): boolean {
        return this.talleresAsignados.includes(tallerId);
    }

    async guardarTalleres() {
        if (!this.selectedGrupo) return;

        this.loadingTalleres = true;

        try {
            const talleresOriginales = this.selectedGrupo.talleres?.map(t => t.id) || [];

            // Talleres a asignar (nuevos)
            const talleresAAgregar = this.talleresAsignados.filter(
                id => !talleresOriginales.includes(id)
            );

            // Talleres a desasignar (removidos)
            const talleresAQuitar = talleresOriginales.filter(
                id => !this.talleresAsignados.includes(id)
            );

            // Asignar nuevos
            for (const tallerId of talleresAAgregar) {
                await firstValueFrom(
                    this.gruposService.asignarTaller(this.selectedGrupo.id_grupo, tallerId)
                );
            }

            // Desasignar removidos
            for (const tallerId of talleresAQuitar) {
                await firstValueFrom(
                    this.gruposService.desasignarTaller(this.selectedGrupo.id_grupo, tallerId)
                );
            }

            this.closeTalleresModal();
            this.cargarGrupos();
        } catch (error: any) {
            console.error('❌ Error al guardar talleres:', error);
            alert(error?.error?.error || 'Error al guardar talleres');
        } finally {
            this.loadingTalleres = false;
        }
    }

    // Manejo de modales
    private openModal() {
        const el = document.getElementById('grupoModal');
        if (!el) return;
        this.modalRef = bootstrap.Modal.getOrCreateInstance(el, {
            backdrop: 'static',
            keyboard: false
        });
        this.modalRef.show();
    }

    closeModal() {
        this.modalRef?.hide();
    }

    private openDeleteModal() {
        const el = document.getElementById('deleteGrupoModal');
        if (!el) return;
        this.deleteModalRef = bootstrap.Modal.getOrCreateInstance(el, {
            backdrop: 'static',
            keyboard: false
        });
        this.deleteModalRef.show();
    }

    closeDeleteModal() {
        this.deleteModalRef?.hide();
        this.selectedGrupo = null;
        this.deleteErrorMessage = '';
    }

    private openTalleresModal() {
        const el = document.getElementById('talleresModal');
        if (!el) return;
        this.talleresModalRef = bootstrap.Modal.getOrCreateInstance(el, {
            backdrop: 'static',
            keyboard: false
        });
        this.talleresModalRef.show();
    }

    closeTalleresModal() {
        this.talleresModalRef?.hide();
        this.selectedGrupo = null;
        this.talleresAsignados = [];
    }
}
