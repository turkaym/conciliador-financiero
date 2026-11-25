# Conciliador Financiero

## Guía funcional y de demostración

Esta guía describe el comportamiento vigente del MVP académico y un recorrido reproducible para docentes y revisores.

> Use únicamente credenciales y CSV ficticios. La aplicación no está preparada para información financiera real.

## 1. Objetivo

Conciliador relaciona movimientos bancarios con comprobantes provenientes de archivos separados. La aplicación valida los datos, propone parejas explicables, conserva la decisión humana y permite revertirla sin perder trazabilidad.

## 2. Navegación actual

| Módulo | Función |
|---|---|
| Importar | Cargar CSV y mostrar esquema, resultado y errores. |
| Consolidado | Consultar movimientos y comprobantes, conciliados o no. |
| Propuestas | Revisar coincidencias automáticas, conciliar manualmente y auditar conciliaciones activas. |
| Historial | Consultar eventos y detalle histórico. |

No existe un módulo Pendientes separado. Los no conciliados se consultan con `Conciliado: No` en Consolidado o desde Propuestas > Manual.

## 3. Flujo principal

1. Iniciar sesión.
2. Importar movimientos eligiendo tipo y banco.
3. Importar comprobantes eligiendo tipo y entidad.
4. Revisar ambos consolidados.
5. Ingresar en Propuestas > Automáticas.
6. Confirmar una coincidencia o buscar coincidencias nuevamente.
7. Si no hay propuesta adecuada, usar Propuestas > Manual.
8. Consultar la conciliación en Auditoría.
9. Descargar el asiento CSV o deshacer la conciliación.
10. Verificar eventos en Historial.

## 4. Importación

La interfaz no solicita Plantilla. Al elegir la fuente obtiene el esquema activo correspondiente y muestra las columnas esperadas.

El importador:

- Admite coma, punto y coma o tabulación.
- Interpreta UTF-8 y CP1252.
- Convierte fechas y decimales según la fuente.
- Conserva datos originales y valores tipados.
- Procesa filas válidas aunque otras fallen.
- Omite duplicados internos e históricos y referencia el registro original.

Estados principales:

- `PROCESADO`: todas las filas válidas.
- `PROCESADO_CON_ERRORES`: combinación de válidas e inválidas.
- `PROCESADO_SIN_VALIDOS`: estructura reconocida, sin filas válidas.
- `FALLIDO`: estructura o procesamiento no interpretable.
- `DUPLICADO`: mismos bytes de un lote que todavía reserva la huella.

## 5. Coincidencias automáticas

Una pareja automática es elegible cuando:

| Criterio | Regla |
|---|---|
| Moneda | Ambos registros son `ARS`. |
| Monto | Igualdad decimal exacta. |
| Fecha | Diferencia máxima de tres días inclusive. |

La referencia se normaliza con `ref-nfkd-v1` y se usa para ordenar y explicar. No habilita ni excluye una pareja.

El matcher se ejecuta:

- Al finalizar una importación con registros válidos.
- Durante una reversión automática.
- Al entrar en Propuestas > Automáticas.
- Al presionar **Buscar coincidencias**.

La sincronización no duplica propuestas generadas ni revive una propuesta rechazada. Es posible que un registro tenga más de una alternativa; al confirmar una, las alternativas incompatibles se marcan `CADUCADA` y desaparecen del listado actualizado.

## 6. Conciliación manual

La pestaña Manual muestra movimientos y comprobantes no conciliados. Los filtros disponibles son:

- Banco o entidad.
- Fecha desde/hasta.
- Monto y tolerancia.
- Referencia.
- Lote.

La conciliación manual permite diferencias de fecha o monto porque representa una decisión explícita del operador. Ambos registros quedan bloqueados y se revalida que sigan disponibles antes de confirmar.

## 7. Auditoría, reversión y exportación

Auditoría muestra solo conciliaciones activas. Sus filtros cubren fechas de conciliación y operaciones, fuentes, monto, referencia, lote y origen.

Al deshacer:

- Se exige un motivo.
- La conciliación pasa a `REVERTIDA`.
- Ambos registros dejan de estar conciliados.
- Si el origen fue automático se genera una propuesta nueva.
- Si fue manual, los registros vuelven a la selección manual y el sincronizador puede volver a detectar una coincidencia automática válida.
- La fila desaparece de Auditoría activa.

La exportación genera un CSV contable filtrado:

- Línea de movimiento: Debe = monto bancario; Haber = 0.
- Línea de comprobante: Debe = 0; Haber = monto del comprobante.
- Diferencia = Debe bancario - Haber comprobante.

## 8. Persistencia de interfaz

Por usuario se conserva en `localStorage`:

- Pestaña y filtros de Consolidado.
- Pestaña de Propuestas.
- Filtros y selecciones manuales.
- Filtros de Auditoría.

Los datos de negocio permanecen en PostgreSQL; `localStorage` guarda solo estado de navegación y token de sesión.

## 9. Demostración recomendada

### Acceso

1. Abrir la aplicación.
2. Ingresar `demo@conciliador.local` / `Demo1234!`.

### Importación y matching

1. Importar `mercado-pago-movimientos-prueba.csv` como Movimiento > Mercado Pago.
2. Importar `mercado-pago-comprobantes-prueba.csv` como Comprobante > Mercado Pago.
3. Revisar el resultado de ambos lotes.
4. Abrir Consolidado y verificar los registros.
5. Abrir Propuestas > Automáticas y revisar las parejas lado a lado.

Si los mismos bytes ya fueron importados, el lote puede quedar `DUPLICADO`. En una base compartida pueden utilizarse registros existentes.

### Confirmación y reversión

1. Confirmar una propuesta.
2. Abrir Auditoría y verificar la conciliación activa.
3. Aplicar filtros y descargar el asiento CSV.
4. Ingresar un motivo y deshacer.
5. Volver a Automáticas: el sistema sincroniza y muestra nuevamente cualquier coincidencia que continúe siendo válida.

## 10. CSV disponibles

En `docs/segunda-entrega/csv/templates/`:

- Banco Nación, Galicia y Mercado Pago para movimientos.
- Mercado Pago, Tienda Nube y ARCA para comprobantes.

En `docs/segunda-entrega/csv/fixtures/` permanecen los casos canónicos válidos, inválidos, duplicados y de estructura incompatible.

## 11. Verificación técnica

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Última validación local:

- 44 pruebas backend aprobadas.
- 17 pruebas frontend aprobadas.
- Build TypeScript/Vite aprobado.

## 12. Limitaciones

- Solo ARS y relaciones 1:1.
- No integra APIs bancarias ni plataformas externas.
- Facturas físicas significa CSV producido previamente por OCR; no se reciben imágenes.
- Sin IA, confirmación autónoma, roles avanzados ni multi-tenancy.
- Despliegues públicos pueden estar detrás de la rama local hasta realizar merge y redeploy.
