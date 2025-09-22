import { Repuesto } from "./repuesto";
import { Taller } from "./taller";

export interface RepuestoTaller {
    id_repuesto_taller: number;
    repuesto: Repuesto;
    taller: Taller;
    precio: number;
    costo: number;
    original: boolean;

    // Predicciones
    pred_1?: number;
    pred_2?: number;
    pred_3?: number;
    pred_4?: number;

    cantidad_minima?: number; // Prediccion_1 por defecto
}