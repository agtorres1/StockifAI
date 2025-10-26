import { Component, Input, OnChanges } from '@angular/core';
import { Chart, ChartConfiguration, Plugin } from 'chart.js';

@Component({
    selector: 'app-gauge-chart',
    templateUrl: './gauge-chart.component.html',
    styleUrls: ['./gauge-chart.component.scss'],
})
export class GaugeChartComponent implements OnChanges {
    @Input() label!: string;
    @Input() porcentaje = 0;
    @Input() total: number | null = 0; // cantidad / $
    @Input() color = '#0d6efd'; // color del arco principal
    @Input() iconClass = 'fa-regular fa-circle';
    @Input() loading = false;

    // Opcionales (tuning)
    @Input() ticksCount = 24; // densidad de “marcas”
    @Input() cutout = '70%'; // grosor del anillo
    @Input() gapSpacing = 6; // separación entre “valor” y “resto”

    data: ChartConfiguration<'doughnut'>['data'] = { datasets: [] };
    opts: ChartConfiguration<'doughnut'>['options'] = {};

    private tickGray = '#f1f3f5';
    private trackGray = '#e9ecef';

    // Texto centrado (una sola vez)
    private static centerLabelRegistered = false;
    private centerLabelPlugin: Plugin<'doughnut'> = {
        id: 'centerLabel',
        afterDraw: (chart) => {
            const { ctx, chartArea } = chart;
            const pct = (chart.config.options as any)?.centerValue as number | undefined;
            if (pct == null) return;

            const x = (chartArea.left + chartArea.right) / 2;
            const y = (chartArea.top + chartArea.bottom) / 2 + 8;

            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.font = '700 18px system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial';
            ctx.fillStyle = '#212529';
            const pctStr = Number.isInteger(pct) ? `${pct}%` : `${pct.toFixed(1)}%`;
            ctx.fillText(pctStr, x, y);
            ctx.restore();
        },
    };

    constructor() {
        if (!GaugeChartComponent.centerLabelRegistered) {
            Chart.register(this.centerLabelPlugin);
            GaugeChartComponent.centerLabelRegistered = true;
        }
    }

    ngOnChanges(): void {
        // dataset principal
        const mainSet = {
            data: [this.porcentaje, 100 - this.porcentaje],
            backgroundColor: [this.color, this.trackGray],
            borderWidth: 0,
            spacing: this.gapSpacing,
            borderRadius: 8,
            weight: 1,
        };

        // anillo de ticks grises
        const tick = 100 / this.ticksCount;
        const tickSet = {
            data: Array(this.ticksCount).fill(tick),
            backgroundColor: Array(this.ticksCount).fill(this.tickGray),
            borderWidth: 0,
            spacing: 4,
            weight: 0.25,
            hoverOffset: 0,
        };

        this.data = {
            labels: [this.label, 'Resto'],
            datasets: [mainSet as any, tickSet as any],
        };

        this.opts = {
            responsive: true,
            maintainAspectRatio: false,
            cutout: this.cutout,
            rotation: -90,
            circumference: 360,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
            animation: { animateRotate: true, duration: 800, easing: 'easeOutQuart' },
        } as any;
        (this.opts as any).centerValue = this.porcentaje;
    }
}
