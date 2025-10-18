import { RepuestoTaller } from './repuesto-taller';

export type NivelAlerta = 'CRITICO' | 'ADVERTENCIA' | 'INFORMATIVO';
export type EstadoAlerta = 'NUEVA' | 'VISTA' | 'DESCARTADA' | 'RESUELTA';
export type TipoAlerta = 'URGENTES' | 'WARNINGS' | 'INFO';

export interface Alerta {
    id: number;
    repuesto_taller: RepuestoTaller;
    nivel: NivelAlerta;
    codigo: string;
    mensaje: string;
    estado: EstadoAlerta;
    fecha_creacion: string;
    datos_snapshot?: any;
}
