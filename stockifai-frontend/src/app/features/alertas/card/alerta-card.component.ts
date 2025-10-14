import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Alerta } from '../../../core/models/alerta';

@Component({
    selector: 'app-alerta-card',
    templateUrl: './alerta-card.component.html',
    styleUrl: './alerta-card.component.scss',
})
export class AlertaCardComponent {
    @Input({ required: true }) alerta!: Alerta;
    @Output() dismiss = new EventEmitter<Alerta>();

    constructor() {}

    onDismiss() {
        this.alerta.estado = 'DESCARTADA';
        this.dismiss.emit(this.alerta);
    }
}
