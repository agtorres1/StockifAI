import { Taller } from "./taller";

export interface Usuario {
    id?: number;
    username: string;
    first_name: string;
    last_name: string;
    email: string;
    telefono: string;
    direccion: string;

    taller?: Taller;
    grupo?: any;
}
