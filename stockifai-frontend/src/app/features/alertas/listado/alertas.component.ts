import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { distinctUntilChanged, firstValueFrom, map, Subscription } from 'rxjs';
import { Alerta, NivelAlerta } from '../../../core/models/alerta';
import { AlertasService } from '../../../core/services/alertas.service';

@Component({
    selector: 'app-alertas',
    templateUrl: './alertas.component.html',
    styleUrl: './alertas.component.scss',
})
export class AlertasComponent implements OnInit, OnDestroy {
    tallerId: number = 1;
    nivelesSeleccionados = new Set<NivelAlerta>();

    alertas: Alerta[] = [];
    loading: boolean = false;
    errorMessage: string = '';

    private subscription?: Subscription;

    private NIVEL_VALUES: NivelAlerta[] = ['CRITICO', 'MEDIO', 'ADVERTENCIA', 'INFORMATIVO'];

    niveles: Array<{ key: NivelAlerta; label: string; class: string }> = [
        { key: 'CRITICO', label: 'Crítico', class: 'critico' },
        { key: 'MEDIO', label: 'Medio', class: 'medio' },
        { key: 'ADVERTENCIA', label: 'Advertencia', class: 'advertencia' },
        { key: 'INFORMATIVO', label: 'Informativo', class: 'informativo' },
    ];

    constructor(private alertasService: AlertasService, private route: ActivatedRoute, private router: Router) {}

    ngOnInit(): void {
        this.nivelesSeleccionados = this.readFromQuery(this.route.snapshot.queryParamMap);

        this.subscription = this.route.queryParamMap
            .pipe(
                map((qpm) => this.readFromQuery(qpm)),
                distinctUntilChanged((a, b) => this.setKey(a) === this.setKey(b))
            )
            .subscribe((set) => {
                this.nivelesSeleccionados = set;
                this.loadData();
            });
    }

    async loadData() {
        this.loading = true;
        try {
            const niveles = Array.from(this.nivelesSeleccionados);
            const res = await firstValueFrom(this.alertasService.getAlertas(this.tallerId, niveles));
            this.alertas = res;
            this.loading = false;
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'Error al cargar las alertas.';
            this.loading = false;
        }
    }

    toggleNivel(nivel: NivelAlerta) {
        if (this.nivelesSeleccionados.has(nivel)) this.nivelesSeleccionados.delete(nivel);
        else this.nivelesSeleccionados.add(nivel);

        this.writeToUrl();
        this.loadData();
    }

    isActive(nivel: NivelAlerta) {
        return this.nivelesSeleccionados.has(nivel);
    }

    setNivel(nivel: NivelAlerta | null) {
        this.router.navigate([], {
            relativeTo: this.route,
            queryParams: nivel ? { nivel } : { nivel: null },
            queryParamsHandling: 'merge',
        });
    }

    onDismiss(alerta: Alerta) {
        this.alertasService.dismissAlerta(alerta.id).subscribe((res) => {
            this.alertasService.triggerResumenRefresh(this.tallerId);
        });
    }

    private writeToUrl(): void {
        const niveles = Array.from(this.nivelesSeleccionados);
        this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { nivel: niveles.length ? niveles : null },
            queryParamsHandling: 'merge',
            replaceUrl: true,
        });
    }

    private readFromQuery(qpm: ParamMap): Set<NivelAlerta> {
        const valores = qpm.getAll('nivel') as NivelAlerta[];
        return new Set(valores.filter((v) => this.NIVEL_VALUES.includes(v)));
    }

    private setKey(s: Set<NivelAlerta>) {
        return [...s].sort().join(',');
    }

    ngOnDestroy(): void {
        this.subscription?.unsubscribe();
    }
}
