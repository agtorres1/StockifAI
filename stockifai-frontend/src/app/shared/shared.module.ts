// src/app/shared/shared.module.ts
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FrecuenciaRotacionPipe } from './pipes/frecuencia-rotacion.pipe';
import { SemaforoAlertasComponent } from './components/semaforo-alertas/semaforo-alertas.component';
import { BaseChartDirective } from 'ng2-charts';
import { GaugeChartComponent } from './components/gauge-chart/gauge-chart.component';

@NgModule({
    declarations: [FrecuenciaRotacionPipe, SemaforoAlertasComponent, GaugeChartComponent],
    imports: [CommonModule, BaseChartDirective],
    exports: [FrecuenciaRotacionPipe, SemaforoAlertasComponent, GaugeChartComponent],
})
export class SharedModule {}
