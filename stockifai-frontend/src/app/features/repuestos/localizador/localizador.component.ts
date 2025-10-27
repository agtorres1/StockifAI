import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import * as L from 'leaflet';
import { Subscription } from 'rxjs';
import { LocalizadorRespuesta, LocalizadorTaller } from '../../../core/models/localizador';
import { LocalizadorService } from '../../../core/services/localizador.service';

// Fix para que salgan los iconos en el mapa
const defaultIcon = L.icon({
  iconUrl:       '/assets/leaflet/images/marker-icon.png',
  iconRetinaUrl: '/assets/leaflet/images/marker-icon-2x.png',
  shadowUrl:     '/assets/leaflet/images/marker-shadow.png',
  iconSize:      [25, 41],
  iconAnchor:    [12, 41],
  popupAnchor:   [1, -34],
  tooltipAnchor: [16, -28],
  shadowSize:    [41, 41],
});
(L.Marker.prototype as any).options.icon = defaultIcon;

@Component({
    selector: 'app-localizador',
    templateUrl: './localizador.component.html',
    styleUrls: ['./localizador.component.scss'],
})
export class LocalizadorComponent implements OnInit, OnDestroy {
    query = '';
    cargando = false;
    resultados: LocalizadorTaller[] = [];
    totalEncontrado = 0;
    mensajeError = '';
    tallerId = 1; // TODO: tomar del usuario autenticado
    repuesto?: LocalizadorRespuesta['repuesto'];
    tallerOrigen?: LocalizadorRespuesta['tallerOrigen'];

    private map?: L.Map;
    private markers: L.Marker[] = [];
    private origenMarker?: L.Marker;
    private busquedaSub?: Subscription;

    constructor(private localizadorService: LocalizadorService, private route: ActivatedRoute) {}

    ngOnInit(): void {
        setTimeout(() => this.initMap(), 0);

        const queryParam = this.route.snapshot.queryParamMap;
        this.query = queryParam.get('search') ?? '';

        if (this.query && this.query != '') {
            this.buscar();
        }
    }

    buscar(): void {
        const normalizada = this.normalizarQuery(this.query);
        if (!normalizada) {
            this.mensajeError = 'Ingresá un número de pieza válido.';
            return;
        }

        this.cargando = true;
        this.mensajeError = '';
        this.busquedaSub?.unsubscribe();

        this.busquedaSub = this.localizadorService.buscarPorNumeroParte(this.tallerId, normalizada).subscribe({
            next: (respuesta) => {
                this.repuesto = respuesta.repuesto;
                this.tallerOrigen = respuesta.tallerOrigen;
                this.totalEncontrado = respuesta.totalCantidad ?? 0;
                this.resultados = respuesta.talleres ?? [];
                this.cargando = false;
                this.renderMarkers();
            },
            error: (err) => {
                console.error('Error buscando repuesto:', err);
                this.resultados = [];
                this.totalEncontrado = 0;
                this.cargando = false;
                this.mensajeError = err?.error?.detail || 'No fue posible localizar el repuesto.';
                this.renderMarkers();
            },
        });
    }

    limpiar(): void {
        this.query = '';
        this.repuesto = undefined;
        this.tallerOrigen = undefined;
        this.totalEncontrado = 0;
        this.mensajeError = '';
        this.resultados = [];
        this.markers.forEach((m) => m.remove());
        this.markers = [];
        this.origenMarker?.remove();
        this.origenMarker = undefined;
        this.map?.setView([-34.6037, -58.3816], 12);
    }

    whatsappUrl(t: LocalizadorTaller): string {
        const numero = t.telefonoE164 ?? '';
        const texto = `Hola, consulto por disponibilidad del repuesto ${this.query.trim()}`;
        return `https://wa.me/${numero}?text=${encodeURIComponent(texto)}`;
    }

    distanciaFormateada(t: LocalizadorTaller): string {
        if (t.distanciaKm == null) return '—';
        return `${t.distanciaKm.toFixed(1)} km`;
    }

    private initMap(): void {
        this.map = L.map('mapa', {
            center: [-34.6037, -58.3816],
            zoom: 12,
        });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap',
        }).addTo(this.map);
    }

    private renderMarkers(): void {
        if (!this.map) return;

        this.markers.forEach((m) => m.remove());
        this.markers = [];
        this.origenMarker?.remove();
        this.origenMarker = undefined;

        if (!this.resultados.length && !this.tallerOrigen) {
            return;
        }

        const bounds = L.latLngBounds([]);

        if (this.tallerOrigen?.latitud != null && this.tallerOrigen?.longitud != null) {
            const origenLatLng = L.latLng(this.tallerOrigen.latitud, this.tallerOrigen.longitud);
            this.origenMarker = L.marker(origenLatLng, {
                title: this.tallerOrigen.nombre,
            }).bindPopup(`<b>${this.tallerOrigen.nombre}</b><br/>Taller origen`);
            this.origenMarker.addTo(this.map!);
            bounds.extend(origenLatLng);
        }

        this.resultados.forEach((t) => {
            if (t.lat == null || t.lng == null) {
                return;
            }
            const detalleGrupos = t.grupos?.length
                ? `<br/><span class="badge bg-info text-dark">${t.grupos.map((g) => g.nombre).join(', ')}</span>`
                : '';
            const distancia = t.distanciaKm != null ? `<br/>Distancia: ${t.distanciaKm.toFixed(1)} km` : '';
            const marker = L.marker([t.lat, t.lng]).bindPopup(
                `<b>${t.nombre}</b><br/>${t.direccion}<br/>Unidades: ${t.cantidad}${distancia}${detalleGrupos}`
            );
            marker.addTo(this.map!);
            this.markers.push(marker);
            bounds.extend([t.lat, t.lng]);
        });

        if (bounds.isValid()) {
            this.map.fitBounds(bounds.pad(0.2));
        }
    }

    ngOnDestroy(): void {
        this.busquedaSub?.unsubscribe();
        this.map?.remove();
    }

    private normalizarQuery(valor: string): string {
        return valor.replace(/\s+/g, '').toUpperCase();
    }
}
