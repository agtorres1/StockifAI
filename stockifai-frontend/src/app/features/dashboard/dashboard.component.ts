import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ChartOptions } from 'chart.js';
import { firstValueFrom, Subscription } from 'rxjs';
import { Alerta } from '../../core/models/alerta';
import { RepuestoTaller } from '../../core/models/repuesto-taller';
import { SaludInventarioChartData, TotalesPorCategoria } from '../../core/models/salud-inventario';
import { AlertasService } from '../../core/services/alertas.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit, OnDestroy {
    tallerId: number = 1;

    loadingUrgentes: boolean = false;
    errorUrgentes: string = '';
    errorSaludInventario: string = '';
    sinAccesoTaller: boolean = false; // ← NUEVO

    page: number = 1;
    pageSize: number = 5;
    totalPages: number = 0;

    listaUrgeComprar: Alerta[] = [];
    exportando: boolean = false;
    exportandoSaludInventario: boolean = false;

    // KPIS
    kpiRotacion = 0;
    objRotacion = 0;
    kpiDiasEnMano = 0;
    objDiasEnMano = 0;
    kpiDeadStock = 0;
    objDeadStock = 0;
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

    intermediaRotacionPercentage: number = 0;

    sub: Subscription | undefined;

    constructor(private alertasService: AlertasService, private authService: AuthService, private router: Router) {}

    ngOnInit(): void {
        this.sub = this.authService.activeTallerId$.subscribe((tallerId) => {
            if (tallerId) {
                this.tallerId = tallerId;
                this.cargarKPIs();
                this.cargarPagina(this.page);
                this.cargarSaludInventario();
            }
        });
    }

    viewForecast(repuestoStock: RepuestoTaller) {
        this.router.navigate(['/repuestos/forecasting'], {
            queryParams: {
                search: repuestoStock.repuesto.numero_pieza,
                viewDetails: true,
            },
        });
    }
    cargarKPIs() {
        this.loadingKpis = true;
        this.alertasService.getKPIsResumen().subscribe({
            next: (data) => {
                // Mapear los datos del backend a las variables del componente
                this.kpiRotacion = data.tasa_rotacion?.valor ?? 0;
                this.objRotacion = data.tasa_rotacion?.objetivo ?? 0;

                this.kpiDiasEnMano = data.dias_en_mano?.valor ?? 0;
                this.objDiasEnMano = data.dias_en_mano?.objetivo ?? 0;

                this.kpiDeadStock = data.dead_stock?.porcentaje ? data.dead_stock.porcentaje / 100 : 0;
                this.objDeadStock = data.dead_stock?.objetivo ? data.dead_stock.objetivo / 100 : 0;

                this.loadingKpis = false;
            },
            error: (err) => {
                console.error('Error al cargar KPIs:', err);
                if (err?.status === 403) {
                    this.sinAccesoTaller = true;
                }
                this.loadingKpis = false;
            },
        });
    }

    // ← MÉTODO ACTUALIZADO
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
                this.sinAccesoTaller = false; // Reset en caso de éxito
            },
            error: (err) => {
                this.loadingUrgentes = false;

                // Manejo específico del 403
                if (err?.status === 403) {
                    this.sinAccesoTaller = true;
                    this.errorUrgentes = 'No tienes acceso a este taller. Contacta al administrador.';
                } else {
                    this.errorUrgentes = err?.message ?? 'Error al cargar las alertas urgentes';
                }
            },
        });
    }

    // ← MÉTODO ACTUALIZADO
    async cargarSaludInventario() {
        try {
            this.loadingSaludInventario = true;
            const res = await firstValueFrom(this.alertasService.getSaludInventario(this.tallerId));
            this.chartData = this.convertirSaludInventarioPorFrecuencia(res);

            console.log('Salud inventario chart data:', this.chartData);

            const deadStock = this.chartData.find((c) => c.frecuencia === 'MUERTO');
            this.deadStockTotal = deadStock?.total_valor ?? 0;
            this.deadStockPercentage = deadStock?.porcentaje ?? 0;

            const altaRotacion = this.chartData.find((c) => c.frecuencia === 'ALTA_ROTACION');
            this.altaRotacionTotal = altaRotacion?.total_valor ?? 0;
            this.altaRotacionPercentage = altaRotacion?.porcentaje ?? 0;

            const lentaRotacion = this.chartData.find((c) => c.frecuencia === 'LENTO');
            this.lentaRotacionTotal = lentaRotacion?.total_valor ?? 0;
            this.lentaRotacionPercentage = lentaRotacion?.porcentaje ?? 0;

            const obsoleto = this.chartData.find((c) => c.frecuencia === 'OBSOLETO');
            this.obsoletoTotal = obsoleto?.total_valor ?? 0;
            this.obsoletoPercentage = obsoleto?.porcentaje ?? 0;

            const intermedia = this.chartData.find((c) => c.frecuencia === 'INTERMEDIO');
            this.intermediaRotacionPercentage = intermedia?.porcentaje ?? 0;

            this.actualizarSaludInventarioResumen();

            this.loadingSaludInventario = false;
            this.saludInventarioError = false; // Reset en caso de éxito
        } catch (error: any) {
            this.loadingSaludInventario = false;

            // Manejo específico del 403
            if (error?.status === 403) {
                this.sinAccesoTaller = true;
                console.warn('Usuario sin acceso al taller para salud de inventario');
            } else {
                this.saludInventarioError = true;
                console.error('Error al cargar salud de inventario:', error);
            }
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
            error: (err) => {
                this.exportando = false;

                // Manejo específico del 403
                if (err?.status === 403) {
                    this.errorUrgentes = 'No tienes permisos para exportar este reporte.';
                } else {
                    this.errorUrgentes = 'No se pudo exportar el Excel.';
                }
            },
        });
    }

    exportarSaludInventario() {
        this.exportandoSaludInventario = true;
        this.alertasService.exportarReporteSaludInventario(this.tallerId).subscribe({
            next: (res) => {
                const blob = res.body!;
                const cd = res.headers.get('Content-Disposition');
                const filename = this.getFilenameFromDisposition(cd) || this.defaultSaludInventarioExcelFilename();
                this.saveBlob(blob, filename);
                this.exportandoSaludInventario = false;
            },
            error: (err) => {
                this.exportandoSaludInventario = false;
                this.errorSaludInventario = 'No se pudo exportar el Excel.';
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

    private defaultSaludInventarioExcelFilename(): string {
        const pad = (n: number) => String(n).padStart(2, '0');
        const d = new Date();
        return `reporte_salud_inventario_${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(
            d.getHours()
        )}${pad(d.getMinutes())}.xlsx`;
    }

    convertirSaludInventarioPorFrecuencia(data: TotalesPorCategoria[]): SaludInventarioChartData[] {
        const acc: Record<string, { items: number; valor: number }> = {};

        for (const cat of data || []) {
            for (const [freq, det] of Object.entries(cat.frecuencias || {})) {
                if (!acc[freq]) acc[freq] = { items: 0, valor: 0 };

                const items = Number(det?.total_items_frecuencia ?? 0);
                const valor = Number(det?.total_valor_frecuencia ?? 0);

                acc[freq].items += isFinite(items) ? items : 0;
                acc[freq].valor += isFinite(valor) ? valor : 0;
            }
        }

        const totalValor = Object.values(acc).reduce((a, b) => a + b.valor, 0);

        const res = Object.entries(acc).map(([frecuencia, { items, valor }]) => ({
            frecuencia,
            total_items: items,
            total_valor: valor,
            porcentaje: totalValor > 0 ? +((valor * 100) / totalValor).toFixed(2) : 0,
        }));

        res.sort((a, b) => b.total_valor - a.total_valor);
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

    ngOnDestroy(): void {
        this.sub?.unsubscribe();
    }

    // Resumen de Salud de inventario
    saludGeneral = 0;
    saludColor = '#28a745';
    saludColorText = '#212529';
    saludLabel = 'SALUDABLE';
    saludIcon = 'fa-solid fa-circle-check';

    healthBarData = {
        labels: [''],
        datasets: [
            {
                data: [this.saludGeneral],
                backgroundColor: this.saludColor,
                borderSkipped: false,
                barThickness: 28,
                borderRadius: { topLeft: 14, bottomLeft: 14, topRight: 0, bottomRight: 0 },
            },
            {
                data: [100 - this.saludGeneral],
                backgroundColor: '#e9ecef',
                borderSkipped: false,
                barThickness: 28,
                borderRadius: { topLeft: 0, bottomLeft: 0, topRight: 14, bottomRight: 14 },
            },
        ],
    };

    healthBarOpts: ChartOptions<'bar'> = {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y' as const,
        animation: { duration: 600, easing: 'easeOutQuart' },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
            x: { display: false, stacked: true, max: 100 },
            y: { display: false, stacked: true },
        },
    };

    actualizarSaludInventarioResumen() {
        // Saludable: Alta Rotación + Intermedio
        const alta = this.altaRotacionPercentage ?? 0;
        const intermedio = this.intermediaRotacionPercentage ?? 0;
        this.saludGeneral = Math.max(0, Math.min(100, alta + intermedio));

        // Umbrales de color/label
        if (this.saludGeneral >= 70) {
            this.saludColor = '#28a745';
            this.saludLabel = 'SALUDABLE';
            this.saludIcon = 'fa-solid fa-circle-check';
        } else if (this.saludGeneral >= 40) {
            this.saludColor = '#ffc107';
            this.saludLabel = 'EN RIESGO';
            this.saludIcon = 'fa-solid fa-triangle-exclamation';
        } else {
            this.saludColor = '#dc3545';
            this.saludLabel = 'CRÍTICO';
            this.saludIcon = 'fa-solid fa-circle-xmark';
        }

        this.healthBarData = {
            ...this.healthBarData,
            datasets: [
                {
                    ...(this.healthBarData.datasets[0] as any),
                    data: [this.saludGeneral],
                    backgroundColor: this.saludColor,
                },
                { ...(this.healthBarData.datasets[1] as any), data: [100 - this.saludGeneral] },
            ],
        };
    }
}
