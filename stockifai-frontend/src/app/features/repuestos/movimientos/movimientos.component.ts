import { Component } from '@angular/core';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-movimientos',
    templateUrl: './movimientos.component.html',
    styleUrl: './movimientos.component.scss',
})
export class MovimientosComponent {
    
    constructor(private titleService: TitleService) {
        this.titleService.setTitle('Movimientos');
    }
}
