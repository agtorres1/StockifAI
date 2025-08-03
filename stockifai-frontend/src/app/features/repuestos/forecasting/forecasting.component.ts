import { Component } from '@angular/core';
import { TitleService } from '../../../core/services/title.service';

@Component({
  selector: 'app-forecasting',
  templateUrl: './forecasting.component.html',
  styleUrl: './forecasting.component.scss'
})
export class ForecastingComponent {

    constructor(private titleService: TitleService){
        this.titleService.setTitle('Forecasting');
    }

}
