# Validación

- **Propósito:** validar estructura/filas, preservar originales y producir registros elegibles tipados.
- **Entrada:** plantilla resuelta y filas CSV interpretadas.
- **Salida:** registros pendientes o errores de campo/lote con claves estables.
- **RF:** RF-03–RF-06; RN-10, RN-11.
- **Dependencias:** definiciones de plantilla y repositorios de registros/errores.
- **Exclusiones:** cambiar originales, corrección difusa y generar propuestas.

MVP-04 usa las columnas de la plantilla activa y conserva los valores originales. Los valores tipados solo se escriben para filas válidas; las filas inválidas y sus errores ordenados permanecen auditables.
