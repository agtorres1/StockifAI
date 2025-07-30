use stockifia_db;


CREATE TABLE provincia (
    id_provincia INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);


CREATE TABLE ciudad (
    id_ciudad INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_provincia INT,
    FOREIGN KEY (id_provincia) REFERENCES provincia(id_provincia)
);


CREATE TABLE barrio (
    id_barrio INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_ciudad INT,
    FOREIGN KEY (id_ciudad) REFERENCES ciudad(id_ciudad)
);


CREATE TABLE direccion (
    id_direccion INT AUTO_INCREMENT PRIMARY KEY,
    calle VARCHAR(100),
    numero VARCHAR(10),
    codigo_postal VARCHAR(10),
    id_barrio INT,
    FOREIGN KEY (id_barrio) REFERENCES barrio(id_barrio)
);


CREATE TABLE Taller (
    id_taller INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100),
    direccion INT,
    telefono VARCHAR(20),
    email VARCHAR(100),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_direccion) REFERENCES Direccion(id_direccion)
);


CREATE TABLE Marca (
	id_marca INT AUTO_INCREMENT PRIMARY KEY,
	nombre varchar(100)
);

CREATE TABLE Categoria (
	id_categoria INT AUTO_INCREMENT PRIMARY KEY,
	nombre varchar(100),
    descripcion varchar(100)
);

CREATE TABLE Grupo (
	id_grupo INT AUTO_INCREMENT PRIMARY KEY,
	nombre varchar(100),
    descripcion varchar(100)
);

CREATE TABLE Grupo_taller (
	id_grupo_taller INT AUTO_INCREMENT PRIMARY KEY,
	id_grupo INT,
    id_taller INT,
	FOREIGN KEY (id_taller) REFERENCES Taller(id_taller),
    FOREIGN KEY (id_grupo) REFERENCES Grupo(id_grupo)
);

CREATE TABLE Usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100),
    email VARCHAR(100),
    telefono VARCHAR(20),
    contrasenia VARCHAR(255) NOT NULL,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    id_taller INT,
    id_grupo INT,
    FOREIGN KEY (id_taller) REFERENCES Taller(id_taller),
    FOREIGN KEY (id_grupo) REFERENCES Grupo(id_grupo)
);

CREATE TABLE Modelo (
	id_modelo INT AUTO_INCREMENT PRIMARY KEY,
	nombre varchar(100),
    id_marca INT,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_marca) REFERENCES Marca(id_marca)
);


CREATE TABLE Repuesto (
	id_repuesto INT AUTO_INCREMENT PRIMARY KEY,
	numero_pieza varchar(100),
    descripcion varchar(100),
    id_marca INT,
    id_categoria INT,
    estado boolean,
    FOREIGN KEY (id_marca) REFERENCES Marca(id_marca),
    FOREIGN KEY (id_categoria) REFERENCES Categoria(id_categoria)
);



CREATE TABLE Repuesto_taller (
	id_repuesto_taller INT AUTO_INCREMENT PRIMARY KEY,
    precio float(100),
    id_repuesto INT,
    id_taller INT,
    original boolean,
    FOREIGN KEY (id_repuesto) REFERENCES Repuesto(id_repuesto),
    FOREIGN KEY (id_taller) REFERENCES Taller(id_taller)
);


CREATE TABLE Rol (
	id_rol INT AUTO_INCREMENT PRIMARY KEY,
    nombre varchar(100),
    descripcion varchar(100)
);

CREATE TABLE Modelo_Repuesto(
	id_modelo_repuesto INT AUTO_INCREMENT PRIMARY KEY,
    id_modelo INT,
    id_repuesto INT,
    FOREIGN KEY (id_repuesto) REFERENCES Repuesto(id_repuesto),
    FOREIGN KEY (id_modelo) REFERENCES Modelo(id_modelo)
	);


CREATE TABLE Deposito (
	id_deposito INT AUTO_INCREMENT PRIMARY KEY,
	nombre varchar(100),
    id_taller INT,
    FOREIGN KEY (id_taller) REFERENCES Taller(id_taller)
);


CREATE TABLE Stock_por_Deposito(
	id_stock_por_deposito INT AUTO_INCREMENT PRIMARY KEY,
    id_repuesto_taller INT,
    cantidad_minima INT,
    cantidad INT,
    frecuencia INT,
    id_deposito INT,
    FOREIGN KEY (id_repuesto_taller) REFERENCES Repuesto_taller(id_repuesto_taller),
    FOREIGN KEY (id_deposito) REFERENCES Deposito(id_deposito)
    
);

CREATE TABLE Ingresos(
	id_ingreso INT AUTO_INCREMENT PRIMARY KEY,
    id_stock_por_deposito INT,
    cantidad INT,
    fecha_de_ingreso DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_stock_por_deposito) REFERENCES Stock_por_Deposito(id_stock_por_deposito)
);

CREATE TABLE Tipo_movimiento(
	id_tipo_movimiento INT AUTO_INCREMENT PRIMARY KEY,
    nombre varchar(100),
    descripcion varchar(100)
);

CREATE TABLE Movimientos(
	id_movimiento INT AUTO_INCREMENT PRIMARY KEY,
    id_stock_por_deposito INT,
    tipo INT,
    cantidad INT,
    fecha_de_ingreso DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_stock_por_deposito) REFERENCES Stock_por_Deposito(id_stock_por_deposito),
	FOREIGN KEY (id_tipo_movimiento) REFERENCES Tipo_movimiento(id_tipo_movimiento)
);

