import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, NavigationEnd, NavigationStart, Params, Router } from '@angular/router';
import { ChartData, ChartDataset, ChartOptions } from 'chart.js';
import { debounceTime, distinctUntilChanged, filter, firstValueFrom, Subject, Subscription } from 'rxjs';
import { ForecastResponse, GraficoCobertura, GraficoDemanda } from '../../../core/models/forecast-response';
import { RepuestoStock } from '../../../core/models/repuesto-stock';
import { AuthService } from '../../../core/services/auth.service';
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
    loadWithDetails: boolean = false;

    forecast: RepuestoStock[] = [];
    page: number = 1;
    pageSize: number = 10;
    totalPages: number = 0;
    errorMessage: string = '';

    @ViewChild('searchInput') searchInput!: ElementRef;
    @ViewChild('detalleRepuesto') detalleRepuesto?: ElementRef<HTMLDivElement>;

    private navigationSub?: Subscription;
    navFromMenu: boolean = false;

    private search$ = new Subject<string>();

    // Detalle
    repuesto?: RepuestoStock;
    forecastRepuesto?: ForecastResponse;

    private searchSub?: Subscription;
    private authSub?: Subscription;

    constructor(
        private titleService: TitleService,
        private stockService: StockService,
        private repuestosService: RepuestosService,
        private authService: AuthService,
        private route: ActivatedRoute,
        private router: Router
    ) {
        this.titleService.setTitle('Forecasting');
    }

    ngOnInit(): void {
        this.getQueryParams();

        this.authSub = this.authService.activeTallerId$.subscribe((id) => {
            if (!id) {
                this.forecast = [];
                this.totalPages = 0;
                this.loading = false;
                return;
            }
            this.tallerId = id;
            this.errorMessage = '';
            
            this.cargarPagina(this.page || 1);
            this.closeDetail();
        });

        this.searchSub = this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((text) => {
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
                    if (this.navFromMenu && url.endsWith('/forecasting')) {
                        this.navFromMenu = false;
                        this.filtro = { searchText: '' };
                        this.page = 1;
                        this.repuesto = undefined;
                        this.cargarPagina(1);
                    }
                }
            });
    }

    onSearchChange(text: string) {
        this.search$.next(text);
    }

    resetear(): void {
        this.filtro = { searchText: '' };
    }

    private cargarPagina(p: number) {
        if (!this.tallerId) return;
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
                this.forecast = (resp.results || []).map((i) => this.stockService.procesarRepuestoStock(i));
                const count = resp.count ?? this.forecast.length;
                this.totalPages = Math.max(1, Math.ceil(count / this.pageSize));
                this.page = p;
                this.loading = false;
                this.errorMessage = '';

                if (this.loadWithDetails && this.forecast.length === 1) {
                    this.viewDetail(this.forecast[0]);
                }
            },
            error: (err) => {
                this.errorMessage = err?.message ?? 'Error al cargar';
                this.loading = false;
            },
        });
    }

    private buildQueryParams(): Params {
        const qp: any = {};

        if (this.filtro.searchText?.trim()) qp.search = this.filtro.searchText.trim();

        return qp;
    }

    private getQueryParams() {
        const qp = this.route.snapshot.queryParamMap;

        this.filtro.searchText = qp.get('search') ?? this.filtro.searchText;
        this.loadWithDetails = qp.get('viewDetails') === 'true';
    }

    async viewDetail(item: RepuestoStock) {
        this.loadingDetails = true;
        this.repuesto = item;

        this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { search: item.repuesto_taller.repuesto.numero_pieza, viewDetails: true },
            replaceUrl: true,
        });

        this.detalleRepuesto?.nativeElement.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
        });

        try {
            const res = await firstValueFrom(
                this.stockService.getRepuestoTallerForecast(this.tallerId, item.repuesto_taller.id_repuesto_taller)
            );
            this.forecastRepuesto = res;
            this.setCobertura(this.forecastRepuesto.grafico_cobertura);
            this.setDemanda(this.forecastRepuesto.grafico_demanda);
            this.loadingDetails = false;
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'No se pudo obtener información extra para este repuesto.';
            this.loadingDetails = false;
        }
    }

    closeDetail() {
        this.repuesto = undefined;
    }

    goPreviousPage() {
        this.cargarPagina(this.page - 1);
    }

    goNextPage() {
        this.cargarPagina(this.page + 1);
    }

    goToPage(p: number) {
        this.cargarPagina(p);
    }

    onPageSizeChange(size: number) {
        this.pageSize = +size;
        this.cargarPagina(1);
    }

    get paginationItems(): Array<number | '…'> {
        const windowSize = 2;
        const total = this.totalPages ?? 0;
        const current = Math.min(Math.max(this.page ?? 1, 1), Math.max(total, 1));

        if (total <= 7) {
            return Array.from({ length: total }, (_, i) => i + 1);
        }

        const left = Math.max(2, current - windowSize);
        const right = Math.min(total - 1, current + windowSize);

        const items: Array<number | '…'> = [1];
        if (left > 2) items.push('…');
        for (let p = left; p <= right; p++) items.push(p);
        if (right < total - 1) items.push('…');
        items.push(total);

        return items;
    }

    ngOnDestroy(): void {
        this.navigationSub?.unsubscribe();
        this.searchSub?.unsubscribe();
        this.authSub?.unsubscribe();
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
                title: { display: true, text: 'Unidades' },
                beginAtZero: true,
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
            label: 'Stock Proyectado',
            data: stock,
            borderRadius: 6,
        };

        const demandaDs: ChartDataset<'line'> = {
            type: 'line',
            label: 'Demanda Proyectada',
            data: demanda,
            tension: 0.25,
            borderWidth: 2,
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
            labels: g.labels,
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
}
