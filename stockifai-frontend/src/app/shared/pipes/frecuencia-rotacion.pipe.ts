import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'frecuenciaRotacion' })
export class FrecuenciaRotacionPipe implements PipeTransform {
    transform(value: string): { label: string; css: string } {
        switch (value) {
            case 'MUERTO':
                return { label: 'Muerto', css: 'bg-secondary' };
            case 'OBSOLETO':
                return { label: 'Obsoleto', css: 'bg-dark' };
            case 'LENTO':
                return { label: 'Rotación lenta', css: 'bg-warning text-dark' };
            case 'INTERMEDIO':
                return { label: 'Rotación intermedia', css: 'bg-primary' };
            case 'ALTA_ROTACION':
                return { label: 'Rotación alta', css: 'bg-danger' };
            default:
                return { label: value ?? 'N/A', css: 'bg-light text-dark' };
        }
    }
}
