import { Taller } from "./taller";

export interface Usuario {
    id?: number;
    username: string;
    first_name: string;
    last_name: string;
    email: string;
    telefono: string;
    direccion?: Direccion;

    taller?: Taller;
    grupo?: any;

    id_grupo?: number;
    id_taller?: number;
    rol_en_grupo?: string;
    rol_en_taller?: string;
}

export interface Direccion {
  id_direccion?: number;
  calle?: string;
  ciudad?: string;
  codigo_postal?: string;
  pais?: string;
}
