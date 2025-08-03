import { Component } from '@angular/core';
import { TitleService } from '../../../core/services/title.service';

@Component({
  selector: 'app-grupos',
  templateUrl: './grupos.component.html',
  styleUrl: './grupos.component.scss'
})
export class TalleresGruposComponent {

    constructor(private titleService: TitleService){
            this.titleService.setTitle('Grupos');
        }

}
