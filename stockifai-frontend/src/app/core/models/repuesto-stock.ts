import { RepuestoTaller } from './repuesto-taller';
import { StockDepositoDetalle } from './stock-por-deposito';

export interface RepuestoStock {
    repuesto_taller: RepuestoTaller;
    stock_total: number;
    depositos: StockDepositoDetalle[];
    mos_en_semanas?: number;

    // FRONTEND
    estaBajoMinimo?: boolean;

    mes_anterior?: number;
    mes_actual?: number;
}
