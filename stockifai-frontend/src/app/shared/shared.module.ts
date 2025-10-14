// src/app/shared/shared.module.ts
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FrecuenciaRotacionPipe } from './pipes/frecuencia-rotacion.pipe';
import { SemaforoAlertasComponent } from './components/semaforo-alertas/semaforo-alertas.component';

@NgModule({
    declarations: [FrecuenciaRotacionPipe, SemaforoAlertasComponent],
    imports: [CommonModule],
    exports: [FrecuenciaRotacionPipe, SemaforoAlertasComponent],
})
export class SharedModule {}
