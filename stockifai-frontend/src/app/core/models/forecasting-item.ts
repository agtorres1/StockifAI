// VA A CAMBIAR DEPENDIENDO DEL BACK, ES PARA TIPIFICAR NADA MAS
export interface ForecastingItem {
    nombre: string;
    sku: string;
    marca: string;
    modelo: string;
    categoria: string;
    stock: number;
    prediccion: number;
    diasRestantes: number;
}