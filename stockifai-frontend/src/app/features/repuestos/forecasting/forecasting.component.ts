import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Params, Router } from '@angular/router';
import { ChartConfiguration, ChartOptions } from 'chart.js';
import { ForecastingItem } from '../../../core/models/forecasting-item';
import { TitleService } from '../../../core/services/title.service';

type ChartKind = 'line';
type BarChartKind = 'bar';

@Component({
    selector: 'app-forecasting',
    templateUrl: './forecasting.component.html',
    styleUrl: './forecasting.component.scss',
})
export class ForecastingComponent implements OnInit {
    filtro: {
        repuesto: string;
        fechaDesde: string;
        fechaHasta: string;
        marca: string | null;
        modelo: string | null;
        categoria: string | null;
    } = {
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

    constructor(private titleService: TitleService, private route: ActivatedRoute, private router: Router) {
        this.titleService.setTitle('Forecasting');
    }

    ngOnInit(): void {
        this.getQueryParams();
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

    private buildQueryParams(): Params {
        const qp: any = {};

        if (this.filtro.repuesto?.trim()) qp.search = this.filtro.repuesto.trim();
        if (this.filtro.marca) qp.marca = this.filtro.marca;
        if (this.filtro.modelo) qp.modelo = this.filtro.modelo;
        if (this.filtro.categoria) qp.categoria = this.filtro.categoria;
        if (this.filtro.fechaDesde) qp.desde = this.filtro.fechaDesde;
        if (this.filtro.fechaHasta) qp.hasta = this.filtro.fechaHasta;

        return qp;
    }

    private getQueryParams() {
        const qp = this.route.snapshot.queryParamMap;

        this.filtro.repuesto = qp.get('search') ?? this.filtro.repuesto;
        this.filtro.marca = qp.get('marca') ?? this.filtro.marca;
        this.filtro.modelo = qp.get('modelo') ?? this.filtro.modelo;
        this.filtro.categoria = qp.get('categoria') ?? this.filtro.categoria;
        this.filtro.fechaDesde = qp.get('desde') ?? this.filtro.fechaDesde;
        this.filtro.fechaHasta = qp.get('hasta') ?? this.filtro.fechaHasta;
    }

    goToDetail(item: any) {
        console.log('detail', item);
    }

    resultados: ForecastingItem[] = [
        {
            nombre: 'Filtro de aire Nissan Kicks',
            sku: 'SKU001',
            marca: 'Toyota',
            modelo: 'Corolla',
            categoria: 'Motor',
            stock: 100,
            prediccion: 97,
            diasRestantes: 7,
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

    // GRAFICO DE DEMANDA PROYECTADA
    // Semanas: 16 históricas + 6 proyectadas = 22 (ajustá a gusto)
    private labels = Array.from({ length: 22 }, (_, i) => `Sem ${i + 1}`);

    // Datos de ejemplo (hardcode): histórico (16), forecast (6)
    private historico: (number | null)[] = [
        82,
        79,
        85,
        88,
        90,
        87,
        92,
        95,
        91,
        94,
        98,
        96,
        99,
        101,
        97,
        100,
        null,
        null,
        null,
        null,
        null,
        null,
    ];

    private forecastMediaSolo: number[] = [102, 104, 103, 101, 99, 98]; // 6 semanas
    private forecastMedia: (number | null)[] = [...Array(16).fill(null), ...this.forecastMediaSolo];

    // Banda de confianza (±4% sobre la media, sólo en semanas de forecast)
    private confPct = 0.04;
    private forecastLower: (number | null)[] = [
        ...Array(16).fill(null),
        ...this.forecastMediaSolo.map((v) => Math.round(v * (1 - this.confPct))),
    ];
    private forecastUpper: (number | null)[] = [
        ...Array(16).fill(null),
        ...this.forecastMediaSolo.map((v) => Math.round(v * (1 + this.confPct))),
    ];

    // Regresión lineal (histórico + media del forecast)
    private tendencia: number[] = this.computeTrendLine(
        this.historico.map((v, i) => v ?? this.forecastMedia[i] ?? null)
    );

    private splitIndex = 16;

    private maxValue = Math.max(...[...this.historico, ...this.forecastUpper].filter((v): v is number => v != null));
    private yMaxLine = Math.ceil(this.maxValue * 1.1); // 10% extra arriba

    data: ChartConfiguration<ChartKind>['data'] = {
        labels: this.labels,
        datasets: [
            // 1) Banda de confianza: lower primero...
            {
                label: 'Conf. (lower)',
                data: this.forecastLower,
                borderColor: 'transparent',
                pointRadius: 0,
                fill: false,
            },
            // ...y upper rellenando contra el anterior (área entre lower y upper)
            {
                label: 'Intervalo de confianza',
                data: this.forecastUpper,
                borderColor: 'transparent',
                backgroundColor: 'rgba(239,108,0,0.12)',
                pointRadius: 0,
                fill: '-1', // rellena hacia el dataset previo (lower)
            },

            // 2) Histórico: línea sólida
            {
                label: 'Demanda histórica',
                data: this.historico,
                borderColor: '#1976d2',
                backgroundColor: 'rgba(25,118,210,0.08)',
                borderWidth: 2,
                tension: 0.35,
                pointRadius: 3,
                spanGaps: true,
                fill: false,
            },

            // 3) Forecast: línea punteada (media)
            {
                label: 'Forecast semanal',
                data: this.forecastMedia,
                borderColor: '#ef6c00',
                backgroundColor: 'rgba(239,108,0,0.10)',
                borderDash: [6, 6],
                borderWidth: 2,
                tension: 0.35,
                pointRadius: 3,
                spanGaps: true,
                fill: false,
            },

            // 4) Tendencia (regresión) sobre todo el período
            {
                label: 'Tendencia',
                data: this.tendencia,
                borderColor: '#455a64',
                borderWidth: 2,
                borderDash: [2, 4],
                pointRadius: 0,
                tension: 0,
                fill: false,
            },

            {
                label: 'Hoy',
                // línea vertical: 2 puntos con el MISMO X y distinto Y
                data: [
                    { x: this.labels[this.splitIndex], y: 75 },
                    { x: this.labels[this.splitIndex], y: this.yMaxLine },
                ],
                borderColor: '#9e9e9e',
                borderWidth: 2,
                borderDash: [6, 6],
                pointRadius: 0,
                fill: false,
                // opcional: que no aparezca en tooltip
                // parsing no es necesario; Chart.js entiende {x,y} por defecto
            } as any,
        ],
    };

    options: ChartOptions<ChartKind> = {
        responsive: true,
        maintainAspectRatio: false,
        devicePixelRatio: 2,
        plugins: {
            title: {
                display: true,
                text: 'Filtro de Aceite Nissan Kicks [Demanda Proyectada]',
                font: { size: 20, weight: 'bold' },
                padding: { bottom: 8 },
            },
            legend: {
                position: 'bottom',
                labels: { filter: (item) => item.text !== 'Conf. (lower)' && item.text !== 'Hoy' },
            },
            tooltip: {
                callbacks: {
                    label: (ctx) => {
                        const v = ctx.parsed.y;
                        return `${ctx.dataset.label}: ${v?.toLocaleString('es-AR')} u.`;
                    },
                },
            },
        },
        scales: {
            x: { grid: { display: false } },
            y: {
                title: { display: true, text: 'Unidades' },
                ticks: { callback: (v) => Number(v).toLocaleString('es-AR') },
            },
        },
    };

    // --- Helpers ---
    private computeTrendLine(series: (number | null)[]): number[] {
        // xs: 1..N, ys: sólo los no-nulos
        const xs: number[] = [];
        const ys: number[] = [];
        series.forEach((val, idx) => {
            if (val != null) {
                xs.push(idx + 1);
                ys.push(val);
            }
        });
        if (xs.length < 2) return Array(series.length).fill(null) as unknown as number[];

        const n = xs.length;
        const sumX = xs.reduce((a, b) => a + b, 0);
        const sumY = ys.reduce((a, b) => a + b, 0);
        const sumXY = xs.reduce((acc, x, i) => acc + x * ys[i], 0);
        const sumX2 = xs.reduce((acc, x) => acc + x * x, 0);

        const denom = n * sumX2 - sumX * sumX || 1;
        const slope = (n * sumXY - sumX * sumY) / denom;
        const intercept = (sumY - slope * sumX) / n;

        // y_hat para todas las semanas (línea completa)
        return Array.from({ length: series.length }, (_, i) => Math.round(intercept + slope * (i + 1)));
    }

    // === GRAFICO BARRAS: STOCK vs DEMANDA PROYECTADA ===

    // Semanas (12 de ejemplo; podés extender)
    stockLabels: string[] = ['Sem 16', 'Sem 17', 'Sem 18', 'Sem 19'];

    // Datos hardcodeados
    private stockSemanal: number[] = [100, 90, 105, 105];
    private demandaProy: number[] = [90, 102, 104, 103];

    // Umbral de “capital inmovilizado”: stock > 1.4 * demanda
    private inmovilizadoThreshold = 1.4;

    // Colores por barra según condición
    private demandaBg = this.demandaProy.map(
        (d, i) => (d > this.stockSemanal[i] ? 'rgba(229,57,53,0.90)' : 'rgba(239,108,0,0.90)') // rojo si hay riesgo
    );
    private demandaBorder = this.demandaProy.map((d, i) =>
        d > this.stockSemanal[i] ? 'rgba(183,28,28,1)' : 'rgba(230,81,0,1)'
    );

    private stockBg = this.stockSemanal.map(
        (s, i) =>
            s > this.demandaProy[i] * this.inmovilizadoThreshold
                ? 'rgba(25,118,210,0.45)' // azul más claro si “sobra” mucho stock
                : 'rgba(25,118,210,0.90)' // azul normal
    );
    private stockBorder = this.stockSemanal.map((s, i) =>
        s > this.demandaProy[i] * this.inmovilizadoThreshold ? 'rgba(13,71,161,1)' : 'rgba(21,101,192,1)'
    );

    stockChartType: BarChartKind = 'bar';

    stockChartData: ChartConfiguration<BarChartKind>['data'] = {
        labels: this.stockLabels,
        datasets: [
            {
                label: 'Stock',
                data: this.stockSemanal,
                backgroundColor: this.stockBg,
                borderColor: this.stockBorder,
                borderWidth: 1,
                barPercentage: 0.8,
                categoryPercentage: 0.6,
            },
            {
                label: 'Demanda proyectada',
                data: this.demandaProy,
                backgroundColor: this.demandaBg,
                borderColor: this.demandaBorder,
                borderWidth: 1,
                barPercentage: 0.8,
                categoryPercentage: 0.6,
            },
        ],
    };

    stockChartOptions: ChartOptions<BarChartKind> = {
        responsive: true,
        maintainAspectRatio: false,
        devicePixelRatio: 2,
        plugins: {
            title: {
                display: true,
                text: 'Nivel de stock',
                font: { size: 20, weight: 'bold' },
                padding: { bottom: 8 },
            },
            legend: { position: 'bottom' },
            tooltip: {
                callbacks: {
                    label: (ctx) => {
                        const val = ctx.parsed.y;
                        const i = ctx.dataIndex;
                        let extra = '';

                        if (ctx.dataset.label === 'Demanda proyectada') {
                            if (this.demandaProy[i] > this.stockSemanal[i]) {
                                extra = ' — Riesgo de faltante';
                            }
                        } else {
                            if (this.stockSemanal[i] > this.demandaProy[i] * this.inmovilizadoThreshold) {
                                extra = ' — Posible capital inmovilizado';
                            }
                        }
                        return `${ctx.dataset.label}: ${val?.toLocaleString('es-AR')} u.${extra}`;
                    },
                },
            },
        },
        scales: {
            x: {
                stacked: false,
                grid: { display: false },
            },
            y: {
                stacked: false,
                title: { display: true, text: 'Unidades' },
                ticks: { callback: (v) => Number(v).toLocaleString('es-AR') },
            },
        },
    };
}
