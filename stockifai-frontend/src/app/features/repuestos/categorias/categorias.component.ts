import { Component, OnInit } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Categoria } from '../../../core/models/categoria';
import { RepuestosService } from '../../../core/services/repuestos.service';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-categorias',
    templateUrl: './categorias.component.html',
    styleUrl: './categorias.component.scss',
})
export class CategoriasComponent implements OnInit {
    categorias: Categoria[] = [];
    loading: boolean = false;
    errorMessage: string = '';

    constructor(private titleService: TitleService, private repuestosService: RepuestosService) {
        this.titleService.setTitle('Categorias');
    }

    async ngOnInit() {
        this.loading = true;

        try {
            const res = await firstValueFrom(this.repuestosService.getCategorias());
            this.categorias = res;
            this.loading = false;
            this.errorMessage = '';
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'Error al cargar';
            this.loading = false;
        }
    }
}
