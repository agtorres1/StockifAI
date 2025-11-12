import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { GaugeChartComponent } from './components/gauge-chart/gauge-chart.component';
import { SelectorTallerComponent } from './components/selector-taller/selector-taller.component';
import { SemaforoAlertasComponent } from './components/semaforo-alertas/semaforo-alertas.component';
import { FrecuenciaRotacionPipe } from './pipes/frecuencia-rotacion.pipe';

@NgModule({
    declarations: [FrecuenciaRotacionPipe, SemaforoAlertasComponent, GaugeChartComponent, SelectorTallerComponent],
    imports: [CommonModule, BaseChartDirective],
    exports: [FrecuenciaRotacionPipe, SemaforoAlertasComponent, GaugeChartComponent, SelectorTallerComponent],
})
export class SharedModule {}
