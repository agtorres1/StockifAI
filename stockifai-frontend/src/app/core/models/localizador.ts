export interface LocalizadorGrupo {
    id: number;
    nombre: string;
    descripcion: string;
    esSubgrupo: boolean;
    grupoPadreId: number | null;
}

export interface LocalizadorRepuestoResumen {
    id: number;
    numero_pieza: string;
    descripcion: string | null;
}

export interface LocalizadorTaller {
    id: number;
    nombre: string;
    direccion: string;
    direccionNormalizada?: string;
    telefono?: string;
    telefonoE164?: string;
    email?: string;
    lat?: number | null;
    lng?: number | null;
    cantidad: number;
    distanciaKm?: number | null;
    grupos: LocalizadorGrupo[];
}

export interface LocalizadorRespuesta {
    repuesto: LocalizadorRepuestoResumen;
    tallerOrigen: {
        id: number;
        nombre: string;
        latitud: number | null;
        longitud: number | null;
    };
    totalCantidad: number;
    talleres: LocalizadorTaller[];
}
