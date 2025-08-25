import { Deposito } from './deposito';
import { Repuesto } from './repuesto';

export interface Movimiento {
    id: number;
    fecha: Date;
    tipo: string;
    cantidad: number;
    deposito: Deposito;
    repuesto: Repuesto;
    externo_id?: number;
    documento?: string;
}
