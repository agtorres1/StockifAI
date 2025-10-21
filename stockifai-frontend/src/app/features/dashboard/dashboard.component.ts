import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Alerta } from '../../core/models/alerta';
import { RepuestoTaller } from '../../core/models/repuesto-taller';
import { AlertasService } from '../../core/services/alertas.service';

@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
    tallerId: number = 1;

    loadingUrgentes: boolean = false;
    errorUrgentes: string = '';

    page: number = 1;
    pageSize: number = 5;
    totalPages: number = 0;

    listaUrgeComprar: Alerta[] = [];
    exportando: boolean = false;

    constructor(private alertasService: AlertasService, private router: Router) {}

    ngOnInit(): void {
        this.cargarPagina(this.page);
    }

    viewForecast(repuestoStock: RepuestoTaller) {
        this.router.navigate(['/repuestos/forecasting'], {
            queryParams: {
                search: repuestoStock.repuesto.numero_pieza,
                viewDetails: true,
            },
        });
    }

    private cargarPagina(p: number) {
        if (p < 1 || (this.totalPages > 0 && p > this.totalPages)) return;

        this.page = p;

        this.loadingUrgentes = true;
        this.alertasService.getAlertas(this.tallerId, ['CRITICO'], this.page, this.pageSize).subscribe({
            next: (res) => {
                this.listaUrgeComprar = res.results;
                this.totalPages = Math.ceil(res.count / this.pageSize);
                this.loadingUrgentes = false;
                this.errorUrgentes = '';
            },
            error: (err) => {
                this.errorUrgentes = err?.message ?? 'Error al cargar';
                this.loadingUrgentes = false;
            },
        });
    }

    exportarListadoUrgeComprar() {
        this.exportando = true;
        this.alertasService.exportarListadoComprarUrgentes(this.tallerId).subscribe({
            next: (res) => {
                const blob = res.body!;
                const cd = res.headers.get('Content-Disposition');
                const filename = this.getFilenameFromDisposition(cd) || this.defaultExcelFilename();
                this.saveBlob(blob, filename);
                this.exportando = false;
            },
            error: () => {
                this.exportando = false;
                this.errorUrgentes = 'No se pudo exportar el Excel.';
            },
        });
    }

    private saveBlob(blob: Blob, filename: string): void {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }

    private getFilenameFromDisposition(cd: string | null): string | null {
        if (!cd) return null;
        const fnStar = cd.match(/filename\*\=([^']*)''([^;]+)/i);
        if (fnStar?.[2]) {
            try {
                return decodeURIComponent(fnStar[2]);
            } catch {
                return fnStar[2];
            }
        }
        const fn = cd.match(/filename=\"?([^\";]+)\"?/i);
        return fn ? fn[1] : null;
    }

    private defaultExcelFilename(): string {
        const pad = (n: number) => String(n).padStart(2, '0');
        const d = new Date();
        return `reporte_urge_comprar_${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(
            d.getHours()
        )}${pad(d.getMinutes())}.xlsx`;
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
}
