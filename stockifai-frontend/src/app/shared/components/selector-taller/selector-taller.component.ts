import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription, firstValueFrom } from 'rxjs';
import { Taller } from '../../../core/models/taller';
import { AuthService } from '../../../core/services/auth.service';
import { TalleresService } from '../../../core/services/talleres.service';

@Component({
    selector: 'app-selector-taller',
    templateUrl: './selector-taller.component.html',
})
export class SelectorTallerComponent implements OnInit, OnDestroy {
    talleres: Taller[] = [];
    selected: Taller | null = null;
    loading = true;
    sub?: Subscription;

    constructor(private authService: AuthService, private talleresService: TalleresService) {}

    async ngOnInit() {
        this.loading = true;

        this.talleres = await firstValueFrom(this.talleresService.getTalleres());

        const current = this.authService.getActiveTaller();
        if (current && this.talleres.some((t) => t.id === current.id)) {
            this.selected = current;
        } else if (this.talleres.length > 0) {
            this.selected = this.talleres[0];
            this.authService.setActiveTaller(this.selected);
        } else {
            this.selected = null;
            this.authService.setActiveTaller(null);
        }

        this.sub = this.authService.activeTaller$.subscribe((t) => (this.selected = t));

        this.loading = false;
    }

    ngOnDestroy() {
        this.sub?.unsubscribe();
    }

    seleccionarTaller(taller: Taller) {
        if (!this.selected || this.selected.id !== taller.id) {
            this.authService.setActiveTaller(taller);
        }
    }

    get disabled(): boolean {
        return !this.loading && this.talleres.length <= 1;
    }

    get selectedNombre(): string {
        return this.selected?.nombre ?? 'Seleccionar taller';
    }
}
