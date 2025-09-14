import { Categoria } from './categoria';
import { Marca } from './marca';

export interface Repuesto {
    numero_pieza: string;
    descripcion: string;
    estado: string;
    marca?: Marca;
    categoria?: Categoria;
}
