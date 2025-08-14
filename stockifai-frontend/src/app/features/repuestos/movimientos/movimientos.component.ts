import { Component, OnInit } from '@angular/core';
import { Deposito } from '../../../core/models/deposito';
import { Movimiento } from '../../../core/models/movimiento';
import { StockService } from '../../../core/services/stock.service';
import { TalleresService } from '../../../core/services/talleres.service';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-movimientos',
    templateUrl: './movimientos.component.html',
    styleUrl: './movimientos.component.scss',
})
export class MovimientosComponent implements OnInit {
    tallerId: number = 1;
    filtro = {
        sku: '',
        deposito: null as number | null,
    };

    depositos: Deposito[] = [];
    loading: boolean = false;
    errorMessage: string = '';

    //depositos: Deposito[] = [
    //    { id: 1, nombre: 'Depósito Central' },
    //    { id: 2, nombre: 'Depósito Secundario' },
    //];

    movimientos: Movimiento[] = [
        {
            tipo: 'ENTRADA',
            cantidad: 5,
            fecha: new Date('2025-08-01'),
            depositoNombre: 'Depósito Central',
            sku: 'ABC123',
        },
        {
            tipo: 'SALIDA',
            cantidad: 2,
            fecha: new Date('2025-08-01'),
            depositoNombre: 'Depósito Central',
            sku: 'ABC123',
        },
        {
            tipo: 'ENTRADA',
            cantidad: 3,
            fecha: new Date('2025-08-02'),
            depositoNombre: 'Depósito Secundario',
            sku: 'XYZ789',
        },
        {
            tipo: 'SALIDA',
            cantidad: 1,
            fecha: new Date('2025-08-02'),
            depositoNombre: 'Depósito Central',
            sku: 'XYZ789',
        },
    ];

    mostrarDialog: boolean = false;

    archivo: File | null = null;
    fecha: string = '';
    errorMsg = '';
    successMsg = '';
    loadingArchivo = false;

    constructor(
        private titleService: TitleService,
        private stockService: StockService,
        private talleresService: TalleresService
    ) {
        this.titleService.setTitle('Movimientos');
        this.fecha = new Date().toISOString().split('T')[0];
    }

    async ngOnInit() {
        this.cargarDepositos();
    }

    async cargarDepositos() {
        try {
            this.loading = true;
            const res = await this.talleresService.getDepositos(this.tallerId);
            console.log('depositos', res);
            this.depositos = res;
            this.loading = false;
        } catch (error: any) {
            this.errorMessage = error.message;
            this.loading = false;
        }
    }

    filtrar() {}

    resetear() {}

    importar() {}

    public onFileChange(event: Event): void {
        const input = event.target as HTMLInputElement | null;
        if (input?.files && input.files.length > 0) {
            this.archivo = input.files[0];
        } else {
            this.archivo = null;
        }
    }

    async submitArchivo() {
        if (!this.archivo) return;

        this.loadingArchivo = true;
        this.errorMsg = '';
        try {
            const res = await this.stockService.importarMovimientos(this.tallerId, this.archivo, this.fecha);
            this.successMsg = 'Archivo subido correctamente';
            this.loadingArchivo = false;
        } catch (err) {
            console.error(err);
            this.errorMsg = 'Error subiendo el archivo';
            this.loadingArchivo = false;
        }
    }
}
