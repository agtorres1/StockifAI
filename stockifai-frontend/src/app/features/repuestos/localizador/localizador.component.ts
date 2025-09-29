import { Component, OnDestroy, OnInit } from '@angular/core';
import * as L from 'leaflet';

type TallerConStock = {
  id: number;
  nombre: string;
  direccion: string;
  lat: number;
  lng: number;
  cantidad: number;
  telefono?: string;     // formato local para mostrar
  telefonoE164?: string; // para WhatsApp (ej: 5491160012345)
  email?: string;
};

@Component({
  selector: 'app-localizador',
  templateUrl: './localizador.component.html',
  styleUrls: ['./localizador.component.scss'],
})
export class LocalizadorComponent implements OnInit, OnDestroy {
  query = '';
  cargando = false;
  resultados: TallerConStock[] = [];

  private map?: L.Map;
  private markers: L.Marker[] = [];

  ngOnInit(): void {
    setTimeout(() => this.initMap(), 0);
  }

  buscar(): void {
    if (!this.query.trim()) return;
    this.cargando = true;

    // ⚠️ MOCK para probar UI (API comentada)
    setTimeout(() => {
      this.resultados = [
        {
          id: 1,
          nombre: 'Taller Central',
          direccion: 'Av. Rivadavia 1234, CABA',
          lat: -34.6083,
          lng: -58.4097,
          cantidad: 4,
          telefono: '11-5555-1234',
          telefonoE164: '5491155551234',
          email: 'central@talleres.com',
        },
        {
          id: 2,
          nombre: 'Mecánica del Sur',
          direccion: 'Calle 50 742, La Plata',
          lat: -34.9215,
          lng: -57.9545,
          cantidad: 2,
          telefono: '221-444-7788',
          telefonoE164: '542214447788',
          email: 'contacto@mecanicadelsur.com',
        },
        {
          id: 3,
          nombre: 'Taller Norte',
          direccion: 'Av. Sarmiento 3500, Rosario',
          lat: -32.9575,
          lng: -60.6394,
          cantidad: 5,
          telefono: '341-555-6677',
          telefonoE164: '543415556677',
          email: 'ventas@tallernorte.com',
        },
        {
          id: 4,
          nombre: 'Garage Oeste',
          direccion: 'Av. San Martín 255, Morón',
          lat: -34.6532,
          lng: -58.6218,
          cantidad: 1,
          telefono: '11-4667-8899',
          telefonoE164: '5491146678899',
          email: 'hola@garageoeste.com',
        },
      ];
      this.cargando = false;
      this.renderMarkers();
    }, 500);

    /*
    // 🔜 Cuando conectes la API real, descomentá y ajustá:
    this.cargando = true;
    this.miServicio.buscarTalleresPorNumeroParte(this.query.trim()).subscribe({
      next: data => { this.resultados = data ?? []; this.cargando = false; this.renderMarkers(); },
      error: err => { this.resultados = []; this.cargando = false; console.error(err); }
    });
    */
  }

  limpiar(): void {
    this.query = '';
    this.resultados = [];
    this.markers.forEach(m => m.remove());
    this.markers = [];
    this.map?.setView([-34.6037, -58.3816], 12);
  }

  whatsappUrl(t: TallerConStock): string {
    const numero = t.telefonoE164 ?? '';
    const texto = `Hola, consulto por disponibilidad del repuesto ${this.query.trim()}`;
    return `https://wa.me/${numero}?text=${encodeURIComponent(texto)}`;
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

    this.markers.forEach(m => m.remove());
    this.markers = [];

    if (!this.resultados.length) return;

    const bounds = L.latLngBounds([]);
    this.resultados.forEach(t => {
      const marker = L.marker([t.lat, t.lng]).bindPopup(
        `<b>${t.nombre}</b><br/>${t.direccion}<br/>Unidades: ${t.cantidad}`
      );
      marker.addTo(this.map!);
      this.markers.push(marker);
      bounds.extend([t.lat, t.lng]);
    });
    this.map.fitBounds(bounds.pad(0.2));
  }

  ngOnDestroy(): void {
    this.map?.remove();
  }
}
