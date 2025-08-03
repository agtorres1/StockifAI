import { Component } from '@angular/core';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-usuarios',
    templateUrl: './usuarios.component.html',
    styleUrl: './usuarios.component.scss',
})
export class TalleresUsuariosComponent {
    constructor(private titleService: TitleService) {
        this.titleService.setTitle('Usuarios');
    }
}
