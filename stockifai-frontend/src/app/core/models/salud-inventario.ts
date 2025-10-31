export interface DetalleFrecuencia {
    critico: number;
    advertencia: number;
    saludable: number;
    sobrestock: number;
    total_items_frecuencia: number;
    total_valor_frecuencia: number;
}

export interface TotalesPorCategoria {
    categoria: string;
    frecuencias: Record<string, DetalleFrecuencia>; // MUERTO, LENTO, ALTA_ROTACION, etc.
    total_items_categoria: number;
    total_valor_categoria: number;
}

export interface SaludInventarioChartData {
    frecuencia: string;
    total_items: number;
    total_valor: number;
    porcentaje: number;
}
