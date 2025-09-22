import { Deposito } from './deposito';
import { RepuestoTaller } from './repuesto-taller';

export interface StockPorDeposito {
    id_stock_por_deposito: number;
    repuesto_taller: RepuestoTaller;
    deposito: Deposito;
    cantidad: number;
}

export interface StockDepositoDetalle {
    deposito: Deposito;
    cantidad: number;
}
