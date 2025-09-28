// src/app/shared/shared.module.ts
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FrecuenciaRotacionPipe } from './pipes/frecuencia-rotacion.pipe';

@NgModule({
    declarations: [FrecuenciaRotacionPipe],
    imports: [CommonModule],
    exports: [FrecuenciaRotacionPipe],
})
export class SharedModule {}
