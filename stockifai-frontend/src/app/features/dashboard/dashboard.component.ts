import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ChartData, ChartOptions, TooltipItem } from 'chart.js';
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

    // Chart
    chartData?: SaludInventarioChartData[];
    pieData: ChartData<'pie'> = { labels: [], datasets: [{ data: [], backgroundColor: [] }] };

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
            const res = await firstValueFrom(this.alertasService.getSaludInventario(this.tallerId));
            this.chartData = this.convertirSaludInventarioPorFrecuencia(res);
            this.setChart(this.chartData);
        } catch (error) {
            
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

    private setChart(src: SaludInventarioChartData[]): void {
        if (!src?.length) {
            this.pieData = { labels: [], datasets: [{ data: [], backgroundColor: [], borderWidth: 0 }] };
            return;
        }

        const labels = src.map((s) => this.prettyLabel(s.frecuencia));
        const values = src.map((s) => s.total);
        const colors = src.map((s) => this.colorFor(s.frecuencia));

        this.pieData = {
            labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 0,
                },
            ],
        };
    }

    private prettyLabel(f: string): string {
        const map: Record<string, string> = {
            ALTA_ROTACION: 'Rotación Alta',
            INTERMEDIO: 'Rotación Intermedia',
            LENTO: 'Rotación Lenta',
            MUERTO: 'Muerto',
            OBSOLETO: 'Obsoleto',
            DESCONOCIDA: 'Desconocida',
        };
        return map[f] ?? f;
    }

    private colorFor(freq: string): string {
        switch (freq) {
            case 'MUERTO':
                return 'rgba(220, 53, 69, 0.65)';
            case 'OBSOLETO':
                return 'rgba(33, 37, 41, 0.65)';
            case 'LENTO':
                return 'rgba(255, 193, 7, 0.65)';
            case 'INTERMEDIO':
                return 'rgba(13, 110, 253, 0.65)';
            case 'ALTA_ROTACION':
                return 'rgba(25, 135, 84, 0.65)';
            default:
                return 'rgba(148, 163, 184, 0.48)';
        }
    }

    pieOptions: ChartOptions<'pie'> = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    usePointStyle: true,
                    pointStyle: 'circle',
                    padding: 16,
                    font: { size: 12 },
                },
            },
            tooltip: {
                backgroundColor: 'rgba(17,24,39,0.9)',
                padding: 10,
                callbacks: {
                    label: (ctx: TooltipItem<'pie'>) => {
                        const label = (ctx.label ?? '').toString();
                        const value = Number(ctx.raw ?? 0);
                        const dataset = ctx.dataset.data as number[];
                        const total = dataset.reduce((a, b) => a + (Number(b) || 0), 0) || 1;
                        const pct = (value * 100) / total;
                        return `${label}: ${value} (${pct.toFixed(2)}%)`;
                    },
                },
            },
        },
    };
}
