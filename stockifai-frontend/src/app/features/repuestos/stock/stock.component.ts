import { Component } from '@angular/core';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-stock',
    templateUrl: './stock.component.html',
    styleUrl: './stock.component.scss',
})
export class StockComponent {
    constructor(private titleService: TitleService) {
        this.titleService.setTitle('Stock');
    }
}
