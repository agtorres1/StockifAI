import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Router } from '@angular/router';
import { Alerta } from '../../../core/models/alerta';

@Component({
    selector: 'app-alerta-card',
    templateUrl: './alerta-card.component.html',
    styleUrl: './alerta-card.component.scss',
})
export class AlertaCardComponent {
    @Input({ required: true }) alerta!: Alerta;
    @Output() dismiss = new EventEmitter<Alerta>();
    @Output() markAsSeen = new EventEmitter<Alerta>();

    constructor(private router: Router) {}

    onDismiss() {
        this.alerta.estado = 'DESCARTADA';
        this.dismiss.emit(this.alerta);
    }

    onMarkAsSeen() {
        this.alerta.estado = 'VISTA';
        this.markAsSeen.emit(this.alerta);
    }

    viewForecast(numeroRepuesto: string) {
        this.router.navigate(['/repuestos/forecasting'], {
            queryParams: {
                search: numeroRepuesto,
                viewDetails: true,
            },
        });
    }
}
