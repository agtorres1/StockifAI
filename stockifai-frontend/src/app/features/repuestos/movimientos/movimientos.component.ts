import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Params, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged, firstValueFrom, forkJoin, Subject, Subscription } from 'rxjs';
import { Deposito } from '../../../core/models/deposito';
import { Movimiento } from '../../../core/models/movimiento';
import { Taller } from '../../../core/models/taller';
import { AlertasService } from '../../../core/services/alertas.service';
import { AuthService } from '../../../core/services/auth.service';
import { StockService } from '../../../core/services/stock.service';
import { TalleresService } from '../../../core/services/talleres.service';
import { TitleService } from '../../../core/services/title.service';

declare var bootstrap: any;

@Component({
    selector: 'app-movimientos',
    templateUrl: './movimientos.component.html',
    styleUrl: './movimientos.component.scss',
})
export class MovimientosComponent implements OnInit, OnDestroy {
    tallerId: number = 1;
    grupoId?: number;
    filtro = { idDeposito: '', searchText: '', desde: '', hasta: '' };

    depositos: Deposito[] = [];
    movimientos: Movimiento[] = [];
    taller?: Taller;
    loading: boolean = false;
    errorMessage: string = '';

    page: number = 1;
    pageSize: number = 10;
    totalPages: number = 0;

    mostrarDialog: boolean = false;

    archivo: File | null = null;
    fecha: string = '';
    errorMsg = '';
    successMsg = '';
    loadingArchivo = false;
    erroresImport: any[] = [];
    initialized = false;

    private search$ = new Subject<string>();

    private subAuth?: Subscription;
    private subSearch?: Subscription;

    stockInicialCargado: boolean = true;
    
    constructor(
        private titleService: TitleService,
        private stockService: StockService,
        private talleresService: TalleresService,
        private route: ActivatedRoute,
        private authService: AuthService,
        private alertasService: AlertasService,
        private router: Router
    ) {
        this.titleService.setTitle('Movimientos');
        this.fecha = new Date().toISOString().split('T')[0];
    }

    ngOnInit(): void {
        if (this.initialized) return;
        this.initialized = true;

        this.subAuth = this.authService.activeTaller$.subscribe((t) => {
            if (!t) {
                this.loading = false;
                return;
            }

            this.tallerId = t.id!;

            this.getQueryParams();
            this.loadData();
        });

        // 🔎 buscador
        this.subSearch = this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((text) => {
            this.page = 1;
            this.filtro.searchText = text;
            this.cargarPagina(this.page);
        });
    }

    loadData() {
        if (!this.tallerId) return;

        this.loading = true;

        forkJoin({
            taller: this.talleresService.getTallerData(this.tallerId),
            depositos: this.talleresService.getDepositos(this.tallerId),
            movimientos: this.stockService.getMovimientos(this.tallerId, this.page, this.pageSize, this.filtro),
        }).subscribe({
            next: ({ taller, depositos, movimientos }) => {
                this.taller = taller;
                this.depositos = Array.isArray((depositos as any)?.depositos)
                    ? (depositos as any).depositos
                    : (depositos as any); // por si tu API a veces envía { depositos: [] }

                this.movimientos = movimientos.results;
                this.totalPages = movimientos.total_pages;

                this.loading = false;
                this.errorMessage = '';
            },
            error: (error) => {
                this.errorMessage = error?.message ?? 'Error al cargar';
                this.loading = false;
            },
        });
    }

    filtrar() {
        this.page = 1;
        this.cargarPagina(this.page);
    }

    resetearFiltros() {
        this.filtro = { idDeposito: '', searchText: '', desde: '', hasta: '' };
        this.filtrar();
    }

    onSearchChange(text: string) {
        this.search$.next(text);
    }

    private cargarPagina(p: number) {
        if (!this.tallerId) return;
        if (p < 1 || p > this.totalPages) return;

        this.page = p;
        this.loading = true;

        this.stockService.getMovimientos(this.tallerId, p, this.pageSize, this.filtro).subscribe({
            next: (resp) => {
                this.movimientos = resp.results;
                this.totalPages = resp.total_pages;
                this.page = resp.page;
                this.pageSize = resp.page_size;
                this.loading = false;
                this.errorMessage = '';
            },
            error: (err) => {
                this.errorMessage = err?.message ?? 'Error al cargar';
                this.loading = false;
            },
        });
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
        if (this.filtro.idDeposito) qp.deposito = this.filtro.idDeposito;
        if (this.filtro.desde) qp.desde = this.filtro.desde;
        if (this.filtro.hasta) qp.hasta = this.filtro.hasta;

        if (this.page && this.page !== 1) qp.page = this.page;
        if (this.pageSize && this.pageSize !== 10) qp.pageSize = this.pageSize;

        return qp;
    }

    private getQueryParams() {
        const qp = this.route.snapshot.queryParamMap;

        this.filtro.idDeposito = qp.get('deposito') ?? this.filtro.idDeposito;
        this.filtro.searchText = qp.get('search') ?? this.filtro.searchText;
        this.filtro.desde = qp.get('desde') ?? this.filtro.desde;
        this.filtro.hasta = qp.get('hasta') ?? this.filtro.hasta;

        const p = parseInt(qp.get('page') ?? '', 10);
        const ps = parseInt(qp.get('pageSize') ?? '', 10);
        if (!Number.isNaN(p) && p > 0) this.page = p;
        if (!Number.isNaN(ps) && ps > 0) this.pageSize = ps;
    }

    ngOnDestroy(): void {
        this.subAuth?.unsubscribe();
        this.subSearch?.unsubscribe();
    }

    // IMPORT MOVIMIENTOS MODAL
    openImportarModal() {
        this.loadingArchivo = false;
        this.erroresImport = [];
        this.successMsg = '';
        this.mostrarDialog = true;
    }

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
            if (this.stockInicialCargado) {
                const res = await firstValueFrom(
                    this.stockService.importarMovimientos(this.tallerId, this.archivo, this.fecha)
                );
                if (res.errores && res.errores.length > 0) {
                    this.erroresImport = res.errores;
                }
                if (res.insertados > 0 || res.ignorados > 0) {
                    this.successMsg = `Se importaron ${res.insertados + res.ignorados} movimientos correctamente`;
                }
                this.alertasService.triggerResumenRefresh(this.tallerId);
                this.closeImportModal(true);
            } else {
                const res = await firstValueFrom(this.stockService.importarStockInicial(this.tallerId, this.archivo));
                if (res.errores && res.errores.length > 0) {
                    this.erroresImport = res.errores;
                }
                if (res.procesados > 0) {
                    this.successMsg = `Se importaron ${res.procesados} ingresos correctamente`;
                }
                this.alertasService.triggerResumenRefresh(this.tallerId);
                this.closeImportModal(true);
            }

            this.loadingArchivo = false;
        } catch (err) {
            this.errorMsg = 'Error al importar el archivo';
            this.loadingArchivo = false;
        }
    }

    closeImportModal(refresh: boolean = true) {
        this.loadingArchivo = false;
        this.erroresImport = [];
        this.mostrarDialog = false;

        const el = document.getElementById('importarMovimientosModal');
        if (el) {
            const modal = bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el);
            modal.hide();
        }

        if (refresh) {
            this.cargarPagina(1);

            this.talleresService.getTallerData(this.tallerId).subscribe({
                next: (data) => {
                    this.taller = data;
                    this.stockInicialCargado = data.stock_inicial_cargado;
                },
                error: (err) => {
                    this.errorMsg = 'Error al cargar los datos del taller';
                },
            });
        }
    }
}
