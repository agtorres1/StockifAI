import { Component, OnInit } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Marca } from '../../../core/models/marca';
import { RepuestosService } from '../../../core/services/repuestos.service';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-marcas',
    templateUrl: './marcas.component.html',
    styleUrl: './marcas.component.scss',
})
export class MarcasComponent implements OnInit {
    marcas: Marca[] = [];
    loading: boolean = false;
    errorMessage: string = '';

    constructor(private titleService: TitleService, private repuestosService: RepuestosService) {
        this.titleService.setTitle('Marcas');
    }

    async ngOnInit() {
        this.loading = true;

        try {
            const res = await firstValueFrom(this.repuestosService.getMarcas());
            this.marcas = res;
            this.loading = false;
            this.errorMessage = '';
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'Error al cargar';
            this.loading = false;
        }
    }
}
