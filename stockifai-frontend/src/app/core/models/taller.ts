export interface Taller {
    id?: number;
    nombre: string;
    direccion: string;
    direccion_normalizada?: string;
    direccion_validada?: boolean;
    telefono: string;
    telefono_e164?: string;
    email: string;
    fecha_creacion: string;
    stock_inicial_cargado: boolean;
    latitud?: number | null;
    longitud?: number | null;
}
