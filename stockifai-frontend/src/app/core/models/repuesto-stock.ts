import { RepuestoTaller } from './repuesto-taller';
import { StockDepositoDetalle } from './stock-por-deposito';

export interface RepuestoStock {
    repuesto_taller: RepuestoTaller;
    stock_total: number;
    depositos: StockDepositoDetalle[];

    // Para front
    estaBajoMinimo?: boolean;
}
