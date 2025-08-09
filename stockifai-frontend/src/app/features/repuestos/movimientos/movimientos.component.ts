import { Component } from '@angular/core';
import { Deposito } from '../../../core/models/deposito';
import { Movimiento } from '../../../core/models/movimiento';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-movimientos',
    templateUrl: './movimientos.component.html',
    styleUrl: './movimientos.component.scss',
})
export class MovimientosComponent {
    filtro = {
        sku: '',
        deposito: null as number | null,
    };

    depositos: Deposito[] = [
        { id: 1, nombre: 'Depósito Central' },
        { id: 2, nombre: 'Depósito Secundario' },
    ];

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

    constructor(private titleService: TitleService) {
        this.titleService.setTitle('Movimientos');
        this.fecha = new Date().toISOString().split('T')[0];
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

    submitArchivo() {
        if (!this.archivo) return;

        const fd = new FormData();
        fd.append('file', this.archivo);
        fd.append('fecha', this.fecha);

        this.errorMsg = '';

        console.log('Enviando archivo...', this.archivo);
    }
}
