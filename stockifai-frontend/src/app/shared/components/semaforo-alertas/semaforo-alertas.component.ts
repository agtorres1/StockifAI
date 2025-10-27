import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { NivelAlerta } from '../../../core/models/alerta';
import { AlertasResumen } from '../../../core/models/alertas-resumen';
import { AlertasService } from '../../../core/services/alertas.service';

@Component({
    selector: 'app-semaforo-alertas',
    templateUrl: './semaforo-alertas.component.html',
    styleUrl: './semaforo-alertas.component.scss',
})
export class SemaforoAlertasComponent implements OnInit, OnDestroy {
    tallerId: number = 1;

    alertas: AlertasResumen = { critico: 0, medio: 0, advertencia: 0, informativo: 0, totalUrgente: 0 };

    subscription?: Subscription;

    constructor(private alertasService: AlertasService, private router: Router) {}

    ngOnInit(): void {
        this.subscription = this.alertasService.summary$(this.tallerId).subscribe((res) => {
            this.alertas = res;
        });
    }

    ngOnDestroy(): void {
        this.subscription?.unsubscribe();
    }

    viewAlerts(nivel: NivelAlerta[]) {
        this.router.navigate(['alertas'], { queryParams: { nivel } });
    }
}
