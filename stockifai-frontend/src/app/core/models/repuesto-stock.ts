import { RepuestoTaller } from './repuesto-taller';
import { StockDepositoDetalle } from './stock-por-deposito';

export interface RepuestoStock {
    repuesto_taller: RepuestoTaller;
    stock_total: number;
    depositos: StockDepositoDetalle[];
    mos_en_semanas?: number;
    dias_de_stock_restantes?: number;
    cantidad_vendida_mes_actual?: number;
    cantidad_vendida_mes_anterior?: number;

    // FRONTEND
    estaBajoMinimo?: boolean;
}
