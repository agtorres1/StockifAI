import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { firstValueFrom, of, Subject, Subscription } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, map, switchMap, tap } from 'rxjs/operators';
import { Alerta, NivelAlerta } from '../../../core/models/alerta';
import { AlertasService } from '../../../core/services/alertas.service';
import { TitleService } from '../../../core/services/title.service';

@Component({
    selector: 'app-alertas',
    templateUrl: './alertas.component.html',
    styleUrls: ['./alertas.component.scss'],
})
export class AlertasComponent implements OnInit, OnDestroy {
    tallerId = 1;
    nivelesSeleccionados = new Set<NivelAlerta>();

    alertas: Alerta[] = [];
    loading = false;
    errorMessage = '';

    page = 1;
    pageSize = 10;
    hasMore = true;
    loadingMore = false;
    private loadedIds = new Set<number>();

    private reqSeq = 0;
    private dataSub?: Subscription;

    private cambiosFiltros$ = new Subject<Set<NivelAlerta>>();

    repuestoTallerId: number | null = null;
    repuestoNumero?: string | null;
    repuestoDescripcion?: string | null;

    private NIVEL_VALUES: NivelAlerta[] = ['CRITICO', 'MEDIO', 'ADVERTENCIA', 'INFORMATIVO'];

    niveles: Array<{ key: NivelAlerta; label: string; class: string }> = [
        { key: 'CRITICO', label: 'Crítico', class: 'critico' },
        { key: 'MEDIO', label: 'Medio', class: 'medio' },
        { key: 'ADVERTENCIA', label: 'Advertencia', class: 'advertencia' },
        { key: 'INFORMATIVO', label: 'Informativo', class: 'informativo' },
    ];

    constructor(private alertasService: AlertasService, private route: ActivatedRoute, private router: Router, private titleService: TitleService) {
        this.titleService.setTitle('Alertas');
    }

    ngOnInit(): void {
        this.loading = true;

        this.nivelesSeleccionados = this.readFromQuery(this.route.snapshot.queryParamMap);

        const repuestoQueryParam = this.route.snapshot.queryParamMap.get('repuesto');
        if (repuestoQueryParam) {
            this.repuestoTallerId = Number(repuestoQueryParam);
            this.repuestoNumero = this.route.snapshot.queryParamMap.get('repuesto_numero');
            this.repuestoDescripcion = this.route.snapshot.queryParamMap.get('repuesto_desc');
        }

        this.dataSub = this.cambiosFiltros$
            .pipe(
                debounceTime(600),

                distinctUntilChanged((a, b) => this.setKey(a) === this.setKey(b)),

                tap((set) => this.writeToUrlFrom(set)),
                tap(() => {
                    this.loading = true;
                    this.errorMessage = '';
                    this.page = 1;
                    this.hasMore = true;
                    this.alertas = [];
                    this.loadedIds.clear();
                }),

                switchMap((set) => {
                    const niveles = Array.from(set);
                    const seq = ++this.reqSeq;

                    const request$ = this.repuestoTallerId
                        ? this.alertasService.getAlertasPorRepuesto(
                              this.tallerId,
                              this.repuestoTallerId,
                              niveles,
                              this.page,
                              this.pageSize
                          )
                        : this.alertasService.getAlertas(this.tallerId, niveles, this.page, this.pageSize);

                    return request$.pipe(
                        map((res) => ({ kind: 'ok' as const, res, seq })),
                        catchError((err) => of({ kind: 'err' as const, err, seq }))
                    );
                })
            )
            .subscribe((msg) => {
                if (msg.seq !== this.reqSeq) return;

                if (msg.kind === 'err') {
                    this.errorMessage = msg.err?.message ?? 'Error al cargar las alertas.';
                    this.loading = false;
                    return;
                }

                const res = msg.res;
                const nuevos = (res?.results ?? []).filter((a) => {
                    if (this.loadedIds.has(a.id)) return false;
                    this.loadedIds.add(a.id);
                    return true;
                });

                this.alertas = nuevos;
                this.hasMore =
                    typeof res?.count === 'number' ? this.alertas.length < res.count : nuevos.length === this.pageSize;
                this.loading = false;
            });

        this.cambiosFiltros$.next(new Set(this.nivelesSeleccionados));
    }

    toggleNivel(nivel: NivelAlerta) {
        if (this.nivelesSeleccionados.has(nivel)) this.nivelesSeleccionados.delete(nivel);
        else this.nivelesSeleccionados.add(nivel);

        this.loading = true;

        this.cambiosFiltros$.next(new Set(this.nivelesSeleccionados));
    }

    async loadMore() {
        if (this.loadingMore || !this.hasMore) return;
        this.loadingMore = true;
        this.errorMessage = '';

        try {
            const niveles = Array.from(this.nivelesSeleccionados);
            const nextPage = this.page + 1;

            const res = await firstValueFrom(
                this.repuestoTallerId
                    ? this.alertasService.getAlertasPorRepuesto(
                          this.tallerId,
                          this.repuestoTallerId,
                          niveles,
                          nextPage,
                          this.pageSize
                      )
                    : this.alertasService.getAlertas(this.tallerId, niveles, nextPage, this.pageSize)
            );

            const nuevos = res.results.filter((a) => {
                if (this.loadedIds.has(a.id)) return false;
                this.loadedIds.add(a.id);
                return true;
            });

            this.alertas = [...this.alertas, ...nuevos];
            this.page = nextPage;
            this.hasMore =
                typeof res.count === 'number' ? this.alertas.length < res.count : nuevos.length === this.pageSize;
        } catch (error: any) {
            this.errorMessage = error?.message ?? 'No se pudieron cargar más alertas.';
        } finally {
            this.loadingMore = false;
        }
    }

    isActive(nivel: NivelAlerta) {
        return this.nivelesSeleccionados.has(nivel);
    }

    onDismiss(alerta: Alerta) {
        this.alertas = this.alertas.filter((a) => a.id !== alerta.id);
        this.loadedIds.delete(alerta.id);

        this.alertasService.dismissAlerta(alerta.id).subscribe({
            next: () => this.alertasService.triggerResumenRefresh(this.tallerId),
            error: () => {
                this.errorMessage = 'No se pudo descartar la alerta.';
            },
        });

        if (this.alertas.length === 0) {
            this.page = -1;
            this.loadMore();
        }
    }

    onMarkAsSeen(alerta: Alerta) {
        this.alertasService.markAsSeenAlerta(alerta.id).subscribe(() => {
            this.alertasService.triggerResumenRefresh(this.tallerId);
        });
    }

    private writeToUrlFrom(set: Set<NivelAlerta>) {
        const niveles = Array.from(set).sort();
        const current = this.route.snapshot.queryParamMap;
        const currentKey = this.setKey(this.readFromQuery(current));
        const nextKey = niveles.join(',');

        const curRep = current.get('repuesto');
        const nextRep = this.repuestoTallerId != null ? String(this.repuestoTallerId) : null;

        if (currentKey === nextKey && curRep === nextRep) return;

        this.router.navigate([], {
            relativeTo: this.route,
            queryParams: {
                nivel: niveles.length ? niveles : null,
                repuesto: nextRep,
                repuesto_numero: this.repuestoNumero ?? null,
                repuesto_desc: this.repuestoDescripcion ?? null,
            },
            queryParamsHandling: 'merge',
            replaceUrl: true,
        });
    }

    private readFromQuery(qpm: ParamMap): Set<NivelAlerta> {
        const valores = (qpm.getAll('nivel') as NivelAlerta[]).filter((v) => this.NIVEL_VALUES.includes(v));
        return new Set(valores);
    }

    private setKey(s: Set<NivelAlerta>) {
        return [...s].sort().join(',');
    }

    ngOnDestroy(): void {
        this.dataSub?.unsubscribe();
    }
}
