import { Component } from '@angular/core';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-forecasting',
    templateUrl: './forecasting.component.html',
    styleUrl: './forecasting.component.scss',
})
export class ForecastingComponent {
    filtro = {
        repuesto: '',
        fechaDesde: '',
        fechaHasta: '',
        marca: null,
        modelo: null,
        categoria: null,
    };

    marcas: string[] = ['Ford', 'Chevrolet', 'Toyota'];
    modelos: string[] = [];
    categorias: string[] = ['Motor', 'Suspensión', 'Frenos'];

    modelosPorMarca: { [marca: string]: string[] } = {
        Ford: ['Focus', 'Fiesta'],
        Chevrolet: ['Cruze', 'Onix'],
        Toyota: ['Corolla', 'Hilux'],
    };

    constructor(private titleService: TitleService) {
        this.titleService.setTitle('Forecasting');
    }

    onMarcaChange(): void {
        const marca = this.filtro.marca;
        this.modelos = marca ? this.modelosPorMarca[marca] || [] : [];
        this.filtro.modelo = null;
    }

    filtrar(): void {
        console.log('Aplicando filtros:', this.filtro);
    }

    resetear(): void {
        this.filtro = {
            repuesto: '',
            fechaDesde: '',
            fechaHasta: '',
            marca: null,
            modelo: null,
            categoria: null,
        };
        this.modelos = [];
    }

    goToDetail(item: any) {
        console.log('detail', item);
    }

    resultados = [
        {
            nombre: 'Filtro de aire',
            sku: 'SKU001',
            marca: 'Toyota',
            modelo: 'Corolla',
            categoria: 'Motor',
            stock: 100,
            prediccion: 5,
            diasRestantes: 0,
        },
        {
            nombre: 'Pastilla de freno',
            sku: 'SKU002',
            marca: 'Ford',
            modelo: 'Focus',
            categoria: 'Frenos',
            stock: 100,
            prediccion: 5,
            diasRestantes: 0,
        },
        {
            nombre: 'Amortiguador trasero',
            sku: 'SKU003',
            marca: 'Chevrolet',
            modelo: 'Onix',
            categoria: 'Suspensión',
            stock: 100,
            prediccion: 5,
            diasRestantes: 0,
        },
        {
            nombre: 'Batería 12V',
            sku: 'SKU004',
            marca: 'Renault',
            modelo: 'Sandero',
            categoria: 'Eléctrico',
            stock: 100,
            prediccion: 5,
            diasRestantes: 0,
        },
        {
            nombre: 'Filtro de aceite',
            sku: 'SKU005',
            marca: 'Volkswagen',
            modelo: 'Gol',
            categoria: 'Motor',
            stock: 100,
            prediccion: 5,
            diasRestantes: 0,
        },
    ];
}
