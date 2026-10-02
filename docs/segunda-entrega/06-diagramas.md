# Diagramas del diseño propuesto

Estos ocho diagramas son vistas complementarias. El [diccionario](05-diccionario-de-datos.md) gobierna restricciones que Mermaid simplifica. Las fuentes se integran aquí deliberadamente para ofrecer renderizado directo en GitHub y evitar ocho archivos `.mmd` redundantes, sin eliminar ningún diagrama previsto.

## 1. Contexto

```mermaid
flowchart LR
 O[Operador autenticado] -->|CSV y decisiones| C[CONCILIADOR]
 C -->|errores, propuestas, pendientes e historial| O
 R[Responsable del proceso] -->|consulta| C
 B[CSV de banco conocido] --> C
 K[CSV de comprobantes conocido] --> C
```

## 2. Casos de uso

```mermaid
flowchart LR
 O((Operador)) --- A[Iniciar sesión]
 O --- I[Importar CSV con fuente y plantilla conocidas]
 O --- P[Revisar propuestas]
 O --- D[Confirmar o rechazar]
 O --- V[Revertir con motivo]
 O --- Q[Consultar pendientes, errores e historial]
 R((Responsable)) --- Q
 I --> N[Validar, deduplicar y normalizar]
 P --> G[Ver criterios y evidencia]
```

## 3. Actividad

```mermaid
flowchart TD
 A[Autenticar; validar fuente/tipo y capturar template_id] --> H[Calcular huella]
 H --> U{¿La huella ya tiene lote original?}
 U -- Sí --> DU[Insertar DUPLICADO con lote_original_id]
 DU --> Z[Registrar evento; sin filas]
 U -- No --> T{¿template_id activo y compatible?}
 T -- No --> PF[Insertar FALLIDO sin plantilla_id + error LOTE; reservar huella]
 PF --> PZ[Conservar solicitud para diagnóstico]
 T -- Sí --> E{¿Se reservó lote original y la estructura es interpretable?}
 E -- Conflicto de huella --> DU
 E -- No --> F[FALLIDO + error de lote]
 E -- Sí --> R[Conservar original y calcular clave]
 R --> X{¿Fila válida?}
 X -- No --> IV[INVALIDO + errores]
 X -- Sí --> Q{¿Clave elegible disponible?}
 Q -- No --> ID[INVALIDO + duplicado + original]
 Q -- Sí --> PE[Subtipo + PENDIENTE]
 IV --> M{¿Más filas?}
 ID --> M
 PE --> M
 M -- Sí --> R
 M -- No --> L[PROCESADO o PROCESADO_CON_ERRORES]
 L --> G[Generar propuestas elegibles]
 G --> D{Decisión humana}
 D -- Confirmar --> C[Conciliar atómicamente]
 D -- Rechazar --> RE[Motivo + evento]
 C --> RV[Posible reversión con motivo]
```

## 4. Módulos

```mermaid
flowchart TB
 subgraph UI[UI React]
  V[Vistas: acceso, cargas, pendientes, propuestas e historial]
 end
 subgraph IN[Adaptador de entrada]
  API[API FastAPI / Pydantic]
 end
 subgraph APP[Capa de aplicación]
  AC[Acceso]
  CA[Catálogos]
  IM[Importación]
  VN[Validación-normalización]
  PR[Propuestas]
  RC[Revisión-conciliación]
  PC[Pendientes-consultas]
  TR[Trazabilidad]
  PORT[Puertos de persistencia]
 end
 subgraph DOM[Dominio]
  D[Entidades y reglas de negocio]
 end
 subgraph OUT[Adaptador de salida]
  PA[Persistencia SQLAlchemy]
 end
 DB[(PostgreSQL)]
 V --> API
 API --> AC
 API --> CA
 API --> IM
 API --> PR
 API --> RC
 API --> PC
 IM --> VN
 IM --> TR
 VN --> TR
 RC --> TR
 AC --> D
 CA --> D
 IM --> D
 VN --> D
 PR --> D
 RC --> D
 PC --> D
 TR --> D
 AC --> PORT
 CA --> PORT
 IM --> PORT
 VN --> PORT
 PR --> PORT
 RC --> PORT
 PC --> PORT
 TR --> PORT
 PA -. implementa .-> PORT
 PA --> DB
```

## 5. Entidad-relación

```mermaid
erDiagram
 USUARIO ||--o{ LOTE_CARGA : carga
 FUENTE_DATOS ||--o{ PLANTILLA_IMPORTACION : ofrece
 FUENTE_DATOS ||--o{ LOTE_CARGA : origina
 PLANTILLA_IMPORTACION ||--|{ CAMPO_PLANTILLA : define
 PLANTILLA_IMPORTACION o|--o{ LOTE_CARGA : interpreta
 LOTE_CARGA o|--o{ LOTE_CARGA : original_de
 LOTE_CARGA ||--o{ REGISTRO_IMPORTADO : contiene
 REGISTRO_IMPORTADO ||--o| MOVIMIENTO_BANCARIO : especializa
 REGISTRO_IMPORTADO ||--o| COMPROBANTE : especializa
 LOTE_CARGA ||--o{ ERROR_VALIDACION : presenta
 REGISTRO_IMPORTADO o|--o{ ERROR_VALIDACION : presenta
 MOVIMIENTO_BANCARIO ||--o{ PROPUESTA_CONCILIACION : candidato
 COMPROBANTE ||--o{ PROPUESTA_CONCILIACION : candidato
 PROPUESTA_CONCILIACION ||--o| CONCILIACION : origina
  USUARIO ||--o{ CONCILIACION : confirma
  USUARIO o|--o{ CONCILIACION : revierte
  USUARIO o|--o{ EVENTO_HISTORIAL : registra
 LOTE_CARGA o|--o{ EVENTO_HISTORIAL : historia
 REGISTRO_IMPORTADO o|--o{ EVENTO_HISTORIAL : historia
 PROPUESTA_CONCILIACION o|--o{ EVENTO_HISTORIAL : historia
 CONCILIACION o|--o{ EVENTO_HISTORIAL : historia
```

## 6. Modelo lógico

```mermaid
classDiagram
 class Usuario {+bigint id PK
+varchar email UQ_CI}
 class FuenteDatos {+bigint id PK
+varchar tipo_origen
+varchar codigo UQ
+boolean activa}
 class PlantillaImportacion {+bigint id PK
+bigint fuente_id FK
+varchar tipo
+int version}
 class CampoPlantilla {+bigint plantilla_id FK
+varchar columna_origen
+varchar campo_canonico}
 class LoteCarga {+bigint id PK
 +bigint fuente_id FK
+bigint plantilla_id FK_NULLABLE
+varchar plantilla_solicitada
+bytea huella_archivo
 +bigint lote_original_id FK
 +varchar estado
 +UQ id_fuente_tipo}
 class RegistroImportado {+bigint id PK
 +bigint lote_id FK_COMPUESTA
 +bigint fuente_id FK_COMPUESTA
 +varchar tipo FK_COMPUESTA
+varchar id_externo
+bytea clave_duplicado
+jsonb datos_originales
+varchar estado}
 class MovimientoBancario {+bigint registro_id PK_FK
+date fecha
+numeric monto
+char moneda}
 class Comprobante {+bigint registro_id PK_FK
+date fecha
+numeric monto
+char moneda}
 class ErrorValidacion {+bigint lote_id FK
+bigint registro_id FK
+varchar codigo}
 class PropuestaConciliacion {+bigint movimiento_id FK
+bigint comprobante_id FK
+varchar estado
+smallint diferencia_dias}
 class Conciliacion {+bigint propuesta_id FK_UQ
+bigint movimiento_id FK
+bigint comprobante_id FK
+bigint confirmada_por FK
+bigint revertida_por FK_NULLABLE
+varchar estado}
 class EventoHistorial {+bigint usuario_id FK_NULLABLE
+bigint lote_id FK_NULLABLE
+bigint registro_id FK_NULLABLE
+bigint propuesta_id FK_NULLABLE
+bigint conciliacion_id FK_NULLABLE
+varchar tipo
+timestamptz ocurrido_en}
 FuenteDatos "1" --> "0..*" PlantillaImportacion
 PlantillaImportacion "1" --> "1..*" CampoPlantilla
 FuenteDatos "1" --> "0..*" LoteCarga
 PlantillaImportacion "0..1" --> "0..*" LoteCarga
 Usuario "1" --> "0..*" LoteCarga : carga
 LoteCarga "0..1" --> "0..*" LoteCarga : original-duplicados
 LoteCarga "1" --> "0..*" RegistroImportado
 RegistroImportado <|-- MovimientoBancario
 RegistroImportado <|-- Comprobante
 LoteCarga "1" --> "0..*" ErrorValidacion
 RegistroImportado "0..1" --> "0..*" ErrorValidacion
 MovimientoBancario "1" --> "0..*" PropuestaConciliacion
 Comprobante "1" --> "0..*" PropuestaConciliacion
 PropuestaConciliacion "1" --> "0..1" Conciliacion
  Usuario "1" --> "0..*" Conciliacion : confirmada_por
  Usuario "0..1" --> "0..*" Conciliacion : revertida_por
 Usuario "0..1" --> "0..*" EventoHistorial : actor
 LoteCarga "0..1" --> "0..*" EventoHistorial : objetivo
 RegistroImportado "0..1" --> "0..*" EventoHistorial : objetivo
 PropuestaConciliacion "0..1" --> "0..*" EventoHistorial : objetivo
 Conciliacion "0..1" --> "0..*" EventoHistorial : objetivo
```

## 7. Estados

```mermaid
stateDiagram-v2
 state Lote {
  [*] --> RECIBIDO
  [*] --> FALLIDO : plantilla desconocida
  RECIBIDO --> EN_VALIDACION
  RECIBIDO --> DUPLICADO
  EN_VALIDACION --> PROCESADO
  EN_VALIDACION --> PROCESADO_CON_ERRORES
  EN_VALIDACION --> FALLIDO
 }
 state Registro {
  [*] --> IMPORTADO
  IMPORTADO --> INVALIDO
  IMPORTADO --> PENDIENTE
  PENDIENTE --> CON_PROPUESTAS
  CON_PROPUESTAS --> PENDIENTE
  CON_PROPUESTAS --> CONCILIADO
  CONCILIADO --> PENDIENTE
  CONCILIADO --> CON_PROPUESTAS
 }
 state Propuesta {
  [*] --> GENERADA
  GENERADA --> CONFIRMADA
  GENERADA --> RECHAZADA
  GENERADA --> CADUCADA
 }
 state Conciliacion {
  [*] --> ACTIVA
  ACTIVA --> REVERTIDA
 }
```

## 8. Secuencia

```mermaid
sequenceDiagram
 actor O as Operador
 participant API
 participant I as ServicioImportacion
 participant P as ServicioPropuestas
 participant R as ServicioRevision
 participant DB as PostgreSQL
 O->>API: cargar CSV(source_id, template_id, tipo)
 API->>I: importar bytes
 I->>I: calcular huella y conservar solicitud
  I->>DB: buscar reserva previa por fuente, tipo y huella
  alt archivo ya recibido
   I->>DB: INSERT DUPLICADO(original_id) + evento y COMMIT
   I-->>O: duplicado, sin registros
  else candidato a lote original
   I->>DB: resolver template_id exacto
   alt plantilla desconocida
    I->>DB: INSERT FALLIDO sin plantilla_id + error LOTE; reservar huella; COMMIT
    Note over I,DB: Si una carrera ya reservó la huella, insertar DUPLICADO del ganador
    I-->>O: fallo consultable o duplicado
   else plantilla conocida
    I->>DB: INSERT lote original ON CONFLICT y COMMIT intento
    alt conflicto concurrente de huella
     I->>DB: INSERT DUPLICADO(original_id) + evento y COMMIT
     I-->>O: duplicado, sin registros
    else lote original
   I->>DB: BEGIN procesamiento
   loop filas
    I->>DB: validar e INSERT elegible ON CONFLICT
    alt fila duplicada o inválida
     I->>DB: INSERT INVALIDO + error
    else fila elegible
     I->>DB: INSERT subtipo y estado PENDIENTE
    end
   end
   alt fallo inesperado
    I->>DB: ROLLBACK procesamiento
    I->>DB: transacción corta FALLIDO + error LOTE + evento y COMMIT
    else procesamiento completo
     I->>DB: finalizar lote + evento y COMMIT
     I->>P: lote procesado; generar automáticamente
     P->>DB: BEGIN y bloquear ambos registros por ID ascendente
     P->>DB: revalidar estados, conciliación activa y criterios
     alt cambió elegibilidad o hay conflicto
      P->>DB: ROLLBACK sin propuesta vigente
     else pareja aún elegible
      P->>DB: INSERT nueva GENERADA; trigger revalida; COMMIT
      Note over P,DB: Terminales históricas; rechazo solo se reevalúa si cambian datos o versión
      P-->>O: candidatas ordenadas por referencia
     end
    end
    end
   end
  end
 O->>API: confirmar propuesta
 API->>R: confirmar(usuario)
 R->>DB: BEGIN; leer IDs inmutables de la pareja sin lock
 R->>DB: bloquear ambos registros por ID ascendente
 R->>DB: bloquear propuesta y revalidar que siga GENERADA
 R->>DB: confirmar propuesta; insertar ACTIVA; trigger caduca incompatibles; evento
 alt conflicto o estado inválido
  DB-->>R: restricción/error
  R->>DB: ROLLBACK
  R-->>O: rechazo sin cambios parciales
 else éxito
  R->>DB: COMMIT
  R-->>O: conciliación activa
 end
```
