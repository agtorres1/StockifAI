import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { Alerta } from '../../core/models/alerta';
import { RepuestoTaller } from '../../core/models/repuesto-taller';
import { SaludInventarioChartData, TotalesPorCategoria } from '../../core/models/salud-inventario';
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

    // KPIS
    kpiRotacion = 6.4;
    objRotacion = 8;
    kpiDiasEnMano = 43;
    objDiasEnMano = 35;
    kpiDeadStock = 0.12;
    objDeadStock = 0.05;
    loadingKpis: boolean = false;

    // Salud de Inventario
    chartData?: SaludInventarioChartData[];
    saludInventarioError: boolean = false;
    loadingSaludInventario: boolean = false;

    deadStockPercentage: number = 0;
    deadStockTotal: number = 0;
    deadStockColor: string = '#dc3545';
    deadStockIcon: string = 'fa-solid fa-skull-crossbones';

    altaRotacionPercentage: number = 0;
    altaRotacionTotal: number = 0;
    altaRotacionColor: string = '#198754';
    altaRotacionIcon: string = 'fa-solid fa-arrows-rotate';

    lentaRotacionPercentage: number = 0;
    lentaRotacionTotal: number = 0;
    lentaRotacionColor: string = '#ffc107';
    lentaRotacionIcon: string = 'fa-solid fa-hourglass-half';

    obsoletoPercentage: number = 0;
    obsoletoTotal: number = 0;
    obsoletoColor: string = '#495057';
    obsoletoIcon: string = 'fa-solid fa-gears';

    constructor(private alertasService: AlertasService, private router: Router) {}

    ngOnInit(): void {
        this.cargarPagina(this.page);
        this.cargarSaludInventario();
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

    async cargarSaludInventario() {
        try {
            this.loadingSaludInventario = true;
            const res = await firstValueFrom(this.alertasService.getSaludInventario(this.tallerId));
            this.chartData = this.convertirSaludInventarioPorFrecuencia(res);

            const deadStock = this.chartData.find((c) => c.frecuencia === 'MUERTO');
            this.deadStockTotal = deadStock?.total ?? 0;
            this.deadStockPercentage = deadStock?.porcentaje ?? 0;

            const altaRotacion = this.chartData.find((c) => c.frecuencia === 'ALTA_ROTACION');
            this.altaRotacionTotal = altaRotacion?.total ?? 0;
            this.altaRotacionPercentage = altaRotacion?.porcentaje ?? 0;

            const lentaRotacion = this.chartData.find((c) => c.frecuencia === 'LENTO');
            this.lentaRotacionTotal = lentaRotacion?.total ?? 0;
            this.lentaRotacionPercentage = lentaRotacion?.porcentaje ?? 0;

            const obsoleto = this.chartData.find((c) => c.frecuencia === 'OBSOLETO');
            this.obsoletoTotal = obsoleto?.total ?? 0;
            this.obsoletoPercentage = obsoleto?.porcentaje ?? 0;

            this.loadingSaludInventario = false;
        } catch (error) {
            this.saludInventarioError = true;
        }
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

    convertirSaludInventarioPorFrecuencia(data: TotalesPorCategoria[]): SaludInventarioChartData[] {
        const acc: Record<string, number> = {};
        for (const cat of data || []) {
            for (const [freq, det] of Object.entries(cat.frecuencias || {})) {
                acc[freq] = (acc[freq] || 0) + (det?.total_items_frecuencia ?? 0);
            }
        }
        const totalGlobal = Object.values(acc).reduce((a, b) => a + b, 0);
        const res = Object.entries(acc).map(([frecuencia, total]) => ({
            frecuencia,
            total,
            porcentaje: totalGlobal ? +((total * 100) / totalGlobal).toFixed(2) : 0,
        }));

        res.sort((a, b) => b.total - a.total);
        return res;
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
