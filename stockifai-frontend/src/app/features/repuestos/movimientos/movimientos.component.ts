import { Component, OnInit } from '@angular/core';
import { debounceTime, distinctUntilChanged, firstValueFrom, forkJoin, Subject } from 'rxjs';
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
    filtro = { idDeposito: '', searchText: '', desde: '', hasta: '' };

    depositos: Deposito[] = [];
    movimientos: Movimiento[] = [];
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

    private search$ = new Subject<string>();

    constructor(
        private titleService: TitleService,
        private stockService: StockService,
        private talleresService: TalleresService
    ) {
        this.titleService.setTitle('Movimientos');
        this.fecha = new Date().toISOString().split('T')[0];
    }

    ngOnInit(): void {
        this.loading = true;

        forkJoin({
            depositos: this.talleresService.getDepositos(this.tallerId),
            movimientos: this.stockService.getMovimientos(this.tallerId, this.page, this.pageSize, this.filtro),
        }).subscribe({
            next: ({ depositos, movimientos }) => {
                this.depositos = depositos;
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

        this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((text) => {
            this.page = 1;
            this.filtro.searchText = text;
            this.cargarPagina(this.page);
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
        if (p < 1 || p > this.totalPages) return;

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

    openImportarModal() {
        this.loadingArchivo = false;
        this.erroresImport = [];
        this.successMsg = '';
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
            const res = await firstValueFrom(
                this.stockService.importarMovimientos(this.tallerId, this.archivo, this.fecha)
            );
            if (res.errores && res.errores.length > 0) {
                this.erroresImport = res.errores;
            }
            if (res.insertados > 0) {
                this.successMsg = `Se importaron ${res.insertados} movimientos correctamente`;
            }
            this.loadingArchivo = false;
        } catch (err) {
            this.errorMsg = 'Error al importar el archivo';
            this.loadingArchivo = false;
        }
    }
}
