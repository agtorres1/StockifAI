import { RepuestoTaller } from './repuesto-taller';

export interface ForecastResponse {
    repuesto_info: RepuestoTaller;
    stock_actual: number;
    dias_de_stock_restantes: number;
    grafico_demanda: GraficoDemanda;
    grafico_cobertura: GraficoCobertura;
}

export type NullableNumber = number | null;

export interface GraficoDemanda {
    historico: NullableNumber[];
    forecastMedia: NullableNumber[];
    forecastLower: NullableNumber[];
    forecastUpper: NullableNumber[];
    tendencia: number[];
    splitIndex: number;
    labels: string[];
}

export interface GraficoCobertura {
    stock_proyectado: number[];
    demanda_proyectada: number[];
    labels: string[];
}
