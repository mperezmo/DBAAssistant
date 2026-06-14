-- Esquema de ejemplo para el análisis de metadata (Sprint 4).
-- Idempotente: borra y recrea. Ejecutar contra la base DBAAssistant.
SET NOCOUNT ON;

IF OBJECT_ID('dbo.pedido_items', 'U') IS NOT NULL DROP TABLE dbo.pedido_items;
IF OBJECT_ID('dbo.pedidos', 'U') IS NOT NULL DROP TABLE dbo.pedidos;
IF OBJECT_ID('dbo.productos', 'U') IS NOT NULL DROP TABLE dbo.productos;
IF OBJECT_ID('dbo.clientes', 'U') IS NOT NULL DROP TABLE dbo.clientes;

CREATE TABLE dbo.clientes (
    id INT IDENTITY PRIMARY KEY,
    nombre NVARCHAR(120) NOT NULL,
    email NVARCHAR(160) NOT NULL,
    ciudad NVARCHAR(80) NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE UNIQUE INDEX IX_clientes_email ON dbo.clientes(email);

CREATE TABLE dbo.productos (
    id INT IDENTITY PRIMARY KEY,
    nombre NVARCHAR(120) NOT NULL,
    precio DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 0
);

CREATE TABLE dbo.pedidos (
    id INT IDENTITY PRIMARY KEY,
    cliente_id INT NOT NULL FOREIGN KEY REFERENCES dbo.clientes(id),
    fecha DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    total DECIMAL(12, 2) NOT NULL DEFAULT 0
);
CREATE INDEX IX_pedidos_cliente ON dbo.pedidos(cliente_id);

CREATE TABLE dbo.pedido_items (
    id INT IDENTITY PRIMARY KEY,
    pedido_id INT NOT NULL FOREIGN KEY REFERENCES dbo.pedidos(id),
    producto_id INT NOT NULL FOREIGN KEY REFERENCES dbo.productos(id),
    cantidad INT NOT NULL,
    precio DECIMAL(10, 2) NOT NULL
);
CREATE INDEX IX_items_pedido ON dbo.pedido_items(pedido_id);
CREATE INDEX IX_items_producto ON dbo.pedido_items(producto_id);

INSERT INTO dbo.clientes (nombre, email, ciudad) VALUES
    ('Marina Vega', 'marina@empresa.com', 'Buenos Aires'),
    ('Tomás Acuña', 'tomas@empresa.com', 'Córdoba'),
    ('Lucía Ferrer', 'lucia@empresa.com', 'Rosario');

INSERT INTO dbo.productos (nombre, precio, stock) VALUES
    ('Teclado mecánico', 25.50, 100),
    ('Mouse inalámbrico', 12.00, 200),
    ('Monitor 27"', 180.00, 40);

INSERT INTO dbo.pedidos (cliente_id, total) VALUES (1, 37.50), (2, 180.00);

INSERT INTO dbo.pedido_items (pedido_id, producto_id, cantidad, precio) VALUES
    (1, 1, 1, 25.50),
    (1, 2, 1, 12.00),
    (2, 3, 1, 180.00);
