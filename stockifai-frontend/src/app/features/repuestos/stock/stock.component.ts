import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, NavigationEnd, NavigationStart, Params, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged, filter, forkJoin, Subject, Subscription } from 'rxjs';
import { Categoria } from '../../../core/models/categoria';
import { Deposito } from '../../../core/models/deposito';
import { RepuestoStock } from '../../../core/models/repuesto-stock';
import { RepuestoTaller } from '../../../core/models/repuesto-taller';
import { RepuestosService } from '../../../core/services/repuestos.service';
import { StockService } from '../../../core/services/stock.service';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-stock',
    templateUrl: './stock.component.html',
    styleUrl: './stock.component.scss',
})
export class StockComponent implements OnInit, AfterViewInit, OnDestroy {
    open = new Set<number>();

    filtro: any = { idCategoria: '', searchText: '' };

    tallerId: number = 1;
    categorias: Categoria[] = [];

    loading: boolean = false;
    errorMessage: string = '';

    stock: RepuestoStock[] = [];
    page: number = 1;
    pageSize: number = 10;
    totalPages: number = 0;

    @ViewChild('searchInput') searchInput!: ElementRef;

    private navigationSub?: Subscription;
    navFromMenu: boolean = false;

    private search$ = new Subject<string>();

    constructor(
        private titleService: TitleService,
        private stockService: StockService,
        private repuestosService: RepuestosService,
        private router: Router,
        private route: ActivatedRoute
    ) {
        this.titleService.setTitle('Stock');
    }

    ngOnInit(): void {
        console.log('stock component');
        this.loading = true;
        this.getQueryParams();

        forkJoin({
            stock: this.stockService.getStock(this.tallerId, this.page, this.pageSize, this.filtro),
            categorias: this.repuestosService.getCategorias(),
        }).subscribe({
            next: ({ stock, categorias }) => {
                this.stock = stock.results.map((i) => this.stockService.procesarRepuestoStock(i));
                this.totalPages = Math.ceil(stock.count / this.pageSize);
                this.categorias = categorias;
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
                        this.filtro = { idCategoria: '', searchText: '' };
                        this.page = 1;
                        this.cargarPagina(1);
                    }
                }
            });
    }

    ngAfterViewInit(): void {
        this.searchInput.nativeElement.focus();
    }

    viewMovimientos(repuestoStock: RepuestoTaller, deposito: Deposito) {
        this.router.navigate(['/repuestos/movimientos'], {
            queryParams: {
                deposito: deposito.id,
                search: repuestoStock.repuesto.numero_pieza,
            },
        });
    }

    viewForecast(repuestoStock: RepuestoTaller) {
        this.router.navigate(['/repuestos/forecasting'], {
            queryParams: {
                search: repuestoStock.repuesto.numero_pieza,
                categoria: this.filtro.idCategoria || null,
                viewDetails: true
            },
        });
    }

    toggle(event: MouseEvent, id: number) {
        event.stopPropagation();
        this.isOpen(id) ? this.open.delete(id) : this.open.add(id);
    }

    isOpen(id: number) {
        return this.open.has(id);
    }

    trackByRepuestoTaller = (_: number, it: RepuestoStock) => it.repuesto_taller.id_repuesto_taller;

    onSearchChange(text: string) {
        this.search$.next(text);
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
        this.stockService.getStock(this.tallerId, p, this.pageSize, this.filtro).subscribe({
            next: (resp) => {
                this.stock = resp.results.map((i) => this.stockService.procesarRepuestoStock(i));
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

    filtrar() {
        this.page = 1;
        this.cargarPagina(this.page);
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

    ngOnDestroy(): void {
        this.navigationSub?.unsubscribe();
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

    private buildQueryParams(): Params {
        const qp: any = {};

        if (this.filtro.searchText?.trim()) qp.search = this.filtro.searchText.trim();
        if (this.filtro.idCategoria) qp.categoria = this.filtro.idCategoria;

        if (this.page && this.page !== 1) qp.page = this.page;
        if (this.pageSize && this.pageSize !== 10) qp.pageSize = this.pageSize;

        return qp;
    }

    private getQueryParams() {
        const qp = this.route.snapshot.queryParamMap;

        this.filtro.searchText = qp.get('search') ?? this.filtro.searchText;
        this.filtro.idCategoria = qp.get('categoria') ?? this.filtro.idCategoria;

        const p = parseInt(qp.get('page') ?? '', 10);
        const ps = parseInt(qp.get('pageSize') ?? '', 10);
        if (!Number.isNaN(p) && p > 0) this.page = p;
        if (!Number.isNaN(ps) && ps > 0) this.pageSize = ps;
    }
}
