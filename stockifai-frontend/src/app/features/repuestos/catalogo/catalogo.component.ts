import { Component, OnInit } from '@angular/core';
import { debounceTime, distinctUntilChanged, firstValueFrom, forkJoin, Subject } from 'rxjs';
import { Categoria } from '../../../core/models/categoria';
import { Marca } from '../../../core/models/marca';
import { Repuesto } from '../../../core/models/repuesto';
import { RepuestosService } from '../../../core/services/repuestos.service';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-catalogo',
    templateUrl: './catalogo.component.html',
    styleUrl: './catalogo.component.scss',
})
export class CatalogoComponent implements OnInit {
    filtro = { searchText: '', idMarca: '', idCategoria: '' };

    marcas: Marca[] = [];
    categorias: Categoria[] = [];
    loading: boolean = false;
    errorMessage: string = '';

    page: number = 1;
    pageSize: number = 10;
    totalPages: number = 0;

    repuestos: Repuesto[] = [];

    private search$ = new Subject<string>();

    archivo: File | null = null;
    errorMsg = '';
    successMsg = '';
    loadingArchivo = false;
    erroresImport: any[] = [];

    constructor(private titleService: TitleService, private repuestosService: RepuestosService) {
        this.titleService.setTitle('Catalogo');
    }

    ngOnInit(): void {
        this.loading = true;

        forkJoin({
            marcas: this.repuestosService.getMarcas(),
            categorias: this.repuestosService.getCategorias(),
            repuestos: this.repuestosService.getRepuestos(this.page, this.pageSize, this.filtro),
        }).subscribe({
            next: ({ marcas, categorias, repuestos }) => {
                this.marcas = marcas;
                this.categorias = categorias;
                this.repuestos = repuestos.results;
                this.totalPages = repuestos.total_pages;
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
        this.filtro = { searchText: '', idMarca: '', idCategoria: '' };
        this.filtrar();
    }

    onSearchChange(text: string) {
        this.search$.next(text);
    }

    private cargarPagina(p: number) {
        if (p < 1 || p > this.totalPages) return;

        this.loading = true;
        this.repuestosService.getRepuestos(p, this.pageSize, this.filtro).subscribe({
            next: (resp) => {
                this.repuestos = resp.results;
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

    // IMPORT CATALOGO MODAL
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
            const res = await firstValueFrom(this.repuestosService.importarRepuestos(this.archivo));
            if (res.errores && res.errores.length > 0) {
                this.erroresImport = res.errores;
            }
            if (res.creados > 0 || res.actualizados > 0 || res.ignorados > 0) {
                this.successMsg = `Se importaron ${
                    res.creados + res.actualizados + res.ignorados
                } repuestos correctamente`;
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
        this.successMsg = '';
        if (refresh) {
            this.cargarPagina(1);
        }
    }
}
