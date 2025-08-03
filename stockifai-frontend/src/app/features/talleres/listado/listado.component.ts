import { Component } from '@angular/core';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-listado',
    templateUrl: './listado.component.html',
    styleUrl: './listado.component.scss',
})
export class TalleresListadoComponent {
    constructor(private titleService: TitleService) {
        this.titleService.setTitle('Talleres');
    }
}
