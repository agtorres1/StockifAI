import { AfterViewInit, Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Params, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged, forkJoin, Subject } from 'rxjs';
import { Categoria } from '../../../core/models/categoria';
import { Deposito } from '../../../core/models/deposito';
import { RepuestoStock } from '../../../core/models/repuesto-stock';
import { RepuestoTaller } from '../../../core/models/repuesto-taller';
import { Taller } from '../../../core/models/taller';
import { RepuestosService } from '../../../core/services/repuestos.service';
import { StockService } from '../../../core/services/stock.service';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-stock',
    templateUrl: './stock.component.html',
    styleUrl: './stock.component.scss',
})
export class StockComponent implements OnInit, AfterViewInit {
    open = new Set<number>();

    repuestos = REPUESTOS_STOCK_MOCK;

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
        this.loading = true;
        this.getQueryParams();

        forkJoin({
            stock: this.stockService.getStock(this.tallerId, this.page, this.pageSize, this.filtro),
            categorias: this.repuestosService.getCategorias(),
        }).subscribe({
            next: ({ stock, categorias }) => {
                this.stock = stock.results.map((i) => this.procesarRepuestoStock(i));
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
                this.stock = resp.results.map((i) => this.procesarRepuestoStock(i));
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

    private procesarRepuestoStock(item: RepuestoStock): RepuestoStock {
        const min = item.repuesto_taller.cantidad_minima;
        if (min != null) {
            item.estaBajoMinimo = item.stock_total < min;
        }
        return item;
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

export const taller1: Taller = {
    id: 501,
    nombre: 'Taller A',
    direccion: '',
    telefono: '',
    email: '',
    fecha_creacion: '',
    stock_inicial_cargado: false,
};

export const REPUESTOS_STOCK_MOCK: RepuestoStock[] = [
    {
        repuesto_taller: {
            id_repuesto_taller: 1001,
            repuesto: {
                numero_pieza: 'FO-123',
                descripcion: 'Filtro de aceite',
                estado: 'activo',
            },
            taller: taller1,
            precio: 12000,
            costo: 8000,
            original: true,
            cantidad_minima: 20,
        },
        stock_total: 25,
        depositos: [
            {
                deposito: { id: 9001, nombre: 'Depósito 1' },
                cantidad: 10,
            },
            {
                deposito: { id: 9002, nombre: 'Depósito 2' },
                cantidad: 15,
            },
        ],
    },
    {
        repuesto_taller: {
            id_repuesto_taller: 1002,
            repuesto: {
                numero_pieza: 'PF-456',
                descripcion: 'Pastillas de freno',
                estado: 'activo',
            },
            taller: taller1,
            precio: 18000,
            costo: 13000,
            original: false,
            cantidad_minima: 120,
        },
        stock_total: 105,
        depositos: [
            {
                deposito: { id: 9001, nombre: 'Depósito 1' },
                cantidad: 100,
            },
            {
                deposito: { id: 9002, nombre: 'Depósito 2' },
                cantidad: 15,
            },
        ],
    },
];
