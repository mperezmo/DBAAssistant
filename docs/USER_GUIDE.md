# Guía de Usuario — DBA Assistant

## 1. Ingresar
- Abrí `http://localhost:3000`.
- **Iniciar sesión** → te redirige a Auth0; al volver, entrás a la app.
- Para cerrar sesión: clic en tu usuario (abajo en la barra lateral).

## 2. Agregar una conexión (Panel Admin)
DBA Assistant arranca **sin** ninguna base. Vos agregás las **instancias** a analizar.

1. Barra lateral → **Sistema → Panel Admin**.
2. **Nueva conexión** → completá *Alias, Host, Puerto, Usuario, Contraseña* (es la
   instancia, no una base puntual) → **Probar** → **Guardar**.
   - Para tu SQL local desde Docker, el host es `host.docker.internal`.
   - El login necesita **VIEW SERVER STATE** para Monitoreo/Optimización.
3. En el Panel Admin también ves la **salud de servicios** y el **rendimiento de la caché**.

## 3. Explorar el esquema (Esquema de BD)
1. **Operaciones → Esquema de BD**.
2. Elegí **Conexión** (instancia) y **Base** (se descubren automáticamente).
3. Clic en una tabla → columnas (PK), índices y claves foráneas.
4. **Refrescar** saltea la caché y vuelve a leer en vivo.

## 4. Monitorear (Monitoreo)
- Elegí la **instancia**. Verás CPU, memoria, sesiones, conexiones, bloqueos,
  sesiones activas y **top queries por CPU**.
- **Auto 10s** refresca solo. Las sesiones con anomalías (bloqueo / CPU alta /
  long-running) se resaltan.

## 5. Generar y ejecutar SQL (Sandbox)
1. Elegí instancia + base.
2. Escribí un pedido en criollo y **Generar con IA** (requiere `ANTHROPIC_API_KEY`),
   o escribí el SQL directo.
3. **Vista previa**: ejecuta dentro de una transacción y hace **ROLLBACK**
   (te dice cuántas filas afectaría). Los `SELECT` muestran resultados.
4. **Ejecutar**: pide confirmación y hace **COMMIT**.
5. Se avisan operaciones riesgosas (DELETE/UPDATE sin WHERE, DROP/TRUNCATE).
6. Abajo, el **historial** de queries ejecutadas.

## 6. Optimizar índices (Optimización)
- Elegí instancia + base. Verás:
  - **Índices faltantes** con su `CREATE INDEX` sugerido.
  - **Índices sin uso** con su `DROP INDEX` sugerido.
- Botón **Copiar** para llevar el statement al Sandbox y ejecutarlo.

## 7. Auditoría
- **Conocimiento → Auditoría**: registro de acciones (altas/bajas de conexiones,
  accesos a esquema, ejecuciones SQL) con usuario, IP, acción y fecha. Filtrable.

## 8. Chat IA
- **Operaciones → Chat IA**: conversá con Claude (genera SQL, explica conceptos,
  recomienda). El historial se guarda en MongoDB. Requiere `ANTHROPIC_API_KEY`.
