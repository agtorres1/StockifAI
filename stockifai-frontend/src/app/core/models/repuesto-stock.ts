import { RepuestoTaller } from './repuesto-taller';
import { StockDepositoDetalle } from './stock-por-deposito';

export interface RepuestoStock {
    repuesto_taller: RepuestoTaller;
    stock_total: number;
    depositos: StockDepositoDetalle[];
    mos_en_semanas?: number;

    // Para front
    estaBajoMinimo?: boolean;
}
