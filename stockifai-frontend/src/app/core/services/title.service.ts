import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class TitleService {
    private _title = signal('StockifAI');
    public readonly title = this._title.asReadonly();

    setTitle(title: string) {
        this._title.set(title);
    }
}
