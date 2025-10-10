import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, NavigationEnd, NavigationStart, Params, Router } from '@angular/router';
import { ChartConfiguration, ChartData, ChartDataset, ChartOptions } from 'chart.js';
import { debounceTime, distinctUntilChanged, filter, firstValueFrom, forkJoin, Subject, Subscription } from 'rxjs';
import { ForecastResponse, GraficoCobertura, GraficoDemanda } from '../../../core/models/forecast-response';
import { ForecastingItem } from '../../../core/models/forecasting-item';
import { RepuestoStock } from '../../../core/models/repuesto-stock';
import { RepuestosService } from '../../../core/services/repuestos.service';
import { StockService } from '../../../core/services/stock.service';
import { TitleService } from '../../../core/services/title.service';

type ChartKind = 'line';
type BarChartKind = 'bar';

@Component({
    selector: 'app-forecasting',
    templateUrl: './forecasting.component.html',
    styleUrl: './forecasting.component.scss',
})
export class ForecastingComponent implements OnInit, OnDestroy {
    filtro: { searchText: string } = { searchText: '' };
    tallerId: number = 1;
    loading: boolean = false;
    showCharts: boolean = false;
    loadingDetails: boolean = false;

    forecast: RepuestoStock[] = [];
    page: number = 1;
    pageSize: number = 10;
    totalPages: number = 0;
    errorMessage: string = '';

    @ViewChild('searchInput') searchInput!: ElementRef;

    private navigationSub?: Subscription;
    navFromMenu: boolean = false;

    private search$ = new Subject<string>();

    // Detalle
    repuesto?: RepuestoStock;
    forecastRepuesto?: ForecastResponse;

    constructor(
        private titleService: TitleService,
        private stockService: StockService,
        private repuestosService: RepuestosService,
        private route: ActivatedRoute,
        private router: Router
    ) {
        this.titleService.setTitle('Forecasting');
    }

    ngOnInit(): void {
        this.loading = true;
        this.getQueryParams();

        forkJoin({
            forecast: this.stockService.getForecastingList(this.tallerId, this.page, this.pageSize, this.filtro),
        }).subscribe({
            next: ({ forecast }) => {
                this.forecast = forecast.results.map((i) => this.stockService.procesarRepuestoStock(i));
                this.totalPages = Math.ceil(forecast.count / this.pageSize);
                this.loading = false;
                this.errorMessage = '';
            },
            error: (error) => {
                this.errorMessage = error?.message ?? 'Error al cargar';
                this.loading = false;
            },
        });

        this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((text) => {
            this.page = 1;
            this.filtro.searchText = text;
            this.cargarPagina(this.page);
        });

        this.navigationSub = this.router.events
            .pipe(filter((ev) => ev instanceof NavigationStart || ev instanceof NavigationEnd))
            .subscribe((ev) => {
                if (ev instanceof NavigationStart) {
                    const nav = this.router.getCurrentNavigation();
                    this.navFromMenu = !!nav?.extras?.state?.['fromMenu'];
                    return;
                }
                if (ev instanceof NavigationEnd) {
                    const url = ev.urlAfterRedirects || ev.url;
                    if (this.navFromMenu && url.endsWith('/stock')) {
                        this.navFromMenu = false;
                        this.filtro = { searchText: '' };
                        this.page = 1;
                        this.cargarPagina(1);
                    }
                }
            });
    }

    onSearchChange(text: string) {
        this.search$.next(text);
    }

    filtrar(): void {
        console.log('Aplicando filtros:', this.filtro);
    }

    resetear(): void {
        this.filtro = { searchText: '' };
    }

    private cargarPagina(p: number) {
        if (p < 1 || (this.totalPages > 0 && p > this.totalPages)) return;

        this.page = p;

        this.router.navigate([], {
            relativeTo: this.route,
            queryParams: this.buildQueryParams(),
            replaceUrl: true,
        });

        this.loading = true;
        this.stockService.getForecastingList(this.tallerId, p, this.pageSize, this.filtro).subscribe({
            next: (resp) => {
                this.forecast = resp.results.map((i) => this.stockService.procesarRepuestoStock(i));
                this.totalPages = Math.ceil(resp.count / this.pageSize);
                this.page = p;
                this.loading = false;
                this.errorMessage = '';
            },
            error: (err) => {
                this.errorMessage = err?.message ?? 'Error al cargar';
                this.loading = false;
            },
        });
    }

    getRandom() {
        return Math.floor(Math.random() * 3) + 1;
    }

    private buildQueryParams(): Params {
        const qp: any = {};

        if (this.filtro.searchText?.trim()) qp.search = this.filtro.searchText.trim();

        return qp;
    }

    private getQueryParams() {
        const qp = this.route.snapshot.queryParamMap;

        this.filtro.searchText = qp.get('search') ?? this.filtro.searchText;
    }

    async viewDetail(item: RepuestoStock) {
        this.loadingDetails = true;
        this.repuesto = item;
        console.log('detail', item);

        try {
            const res = await firstValueFrom(
                this.stockService.getRepuestoTallerForecast(this.tallerId, item.repuesto_taller.id_repuesto_taller)
            );
            console.log('Repuesto taller forecast', res);
            this.forecastRepuesto = res;
            this.setCobertura(this.forecastRepuesto.grafico_cobertura);
            this.setDemanda(this.forecastRepuesto.grafico_demanda);
            this.loadingDetails = false;
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'No se pudo obtener información extra para este repuesto.';
        }
    }

    ngOnDestroy(): void {
        this.navigationSub?.unsubscribe();
    }

    // GRAFICO DE COBERTURA
    coberturaData: ChartData<'bar' | 'line'> = {
        labels: [],
        datasets: [],
    };

    coberturaOptions: ChartOptions<'bar' | 'line'> = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                title: { display: true, text: 'Stock (unidades)' },
                beginAtZero: true,
                border: { display: false },
                grace: '15%',
                ticks: {
                    precision: 0,
                },
            },
            y1: {
                position: 'right',
                title: { display: true, text: 'Demanda (unidades)' },
                beginAtZero: true,
                grid: { drawOnChartArea: false },
                border: { display: false },
                grace: '15%',
                ticks: {
                    precision: 0,
                },
            },
            x: {
                border: { display: false },
            },
        },
        plugins: {
            legend: { position: 'top' },
            tooltip: {
                callbacks: {
                    label: (ctx) => {
                        const v = ctx.parsed.y;
                        const ds = ctx.dataset.label ?? '';
                        return `${ds}: ${v ?? 0} u.`;
                    },
                },
            },
        },
    };

    private setCobertura(gc: GraficoCobertura) {
        const labels = gc.labels ?? [];
        const stock = (gc.stock_proyectado ?? []).map((n) => n ?? 0);
        const demanda = (gc.demanda_proyectada ?? []).map((n) => n ?? 0);

        const stockDs: ChartDataset<'bar'> = {
            type: 'bar',
            label: 'Stock Proyectado (u.)',
            data: stock,
            borderRadius: 6,
        };

        const demandaDs: ChartDataset<'line'> = {
            type: 'line',
            label: 'Demanda Proyectada (u.)',
            data: demanda,
            yAxisID: 'y1',
            tension: 0.25,
            pointRadius: 3,
            pointHoverRadius: 5,
        };

        this.coberturaData = {
            labels,
            datasets: [stockDs, demandaDs],
        };
    }

    // GRAFICO DE DEMANDA
    demandaData: ChartData<'line'> = {
        labels: [],
        datasets: [],
    };

    demandaOptions: ChartOptions<'line'> = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
            y: {
                beginAtZero: true,
                title: { display: true, text: 'Unidades' },
                grace: '10%',
                ticks: {
                    precision: 0,
                },
            },
            x: {
                title: { display: true, text: 'Semanas' },
            },
        },
        plugins: {
            legend: { position: 'top' },
            tooltip: {
                callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y ?? 0} u.`,
                },
            },
        },
    };

    private setDemanda(g: GraficoDemanda) {
        const hist = g.historico ?? [];
        const forecast = g.forecastMedia ?? [];
        const tendencia = g.tendencia ?? [];
        const total = Math.max(hist.length, forecast.length);
        const labels = Array.from({ length: total }, (_, i) => `Sem ${i + 1}`);

        const split = g.splitIndex ?? hist.length;

        this.demandaData = {
            labels,
            datasets: [
                {
                    label: 'Demanda Histórica',
                    data: hist,
                    tension: 0.2,
                    pointRadius: 3,
                },
                {
                    label: 'Forecast',
                    data: forecast,
                    borderDash: [5, 5],
                    tension: 0.2,
                    pointRadius: 3,
                },
                {
                    label: 'Tendencia',
                    data: tendencia,
                    borderWidth: 1.5,
                    borderDash: [2, 2],
                    pointRadius: 0,
                },
            ],
        };
    }

    /*
    marcas: string[] = ['Ford', 'Chevrolet', 'Toyota'];
    modelos: string[] = [];
    categorias: string[] = ['Motor', 'Suspensión', 'Frenos'];

    modelosPorMarca: { [marca: string]: string[] } = {
        Ford: ['Focus', 'Fiesta'],
        Chevrolet: ['Cruze', 'Onix'],
        Toyota: ['Corolla', 'Hilux'],
    };

    onMarcaChange(): void {
        const marca = this.filtro.marca;
        this.modelos = marca ? this.modelosPorMarca[marca] || [] : [];
        this.filtro.modelo = null;
    } 
    */
}
