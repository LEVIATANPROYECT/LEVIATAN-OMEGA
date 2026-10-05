# LEVIATÁN Ω — Política de moderación

**STATUS: PRE-T0 — DRAFT**

## 1. Objetivo

La moderación protege la integridad de LEVIATÁN Ω sin modificar artificialmente sus resultados.

Una contribución no se acepta o rechaza por ser favorable o crítica con el proyecto.

## 2. Criterios de aceptación

Una contribución puede aceptarse cuando:

- contiene una aportación real;
- es pertinente para LEVIATÁN Ω;
- cumple las condiciones de participación;
- supera las comprobaciones técnicas;
- no vulnera las reglas de rechazo de este documento.

## 3. Criterios de rechazo

Se rechazará una entrada cuando:

- sea ilegal;
- vulnere derechos de terceros;
- contenga datos personales innecesarios propios o de terceros;
- constituya spam;
- sea manifiestamente ajena al experimento;
- intente manipular fraudulentamente el registro;
- fabrique participantes, acontecimientos o resultados;
- utilice un token inválido o ya consumido;
- incumpla las condiciones de participación aplicables.

## 4. Neutralidad

No son motivos de rechazo:

- criticar LEVIATÁN Ω;
- considerar que el experimento fracasará;
- cuestionar el precio de salida;
- señalar errores;
- proponer modificaciones;
- expresar una valoración negativa.

Las críticas válidas forman parte del experimento.

## 5. Estados

Cada entrada podrá encontrarse en uno de estos estados:

- PENDIENTE_VALIDACIÓN
- PENDIENTE_MODERACIÓN
- ACEPTADA
- RECHAZADA
- EXCLUIDA
- RETIRADA

## 6. Registro del rechazo

Una entrada rechazada conservará en el registro canónico únicamente:

- ID interno;
- estado RECHAZADA;
- código o motivo del rechazo;
- información no personal necesaria para preservar la genealogía.

El contenido rechazado no se publicará cuando hacerlo resulte inapropiado.

Una entrada rechazada no cuenta como contribución aceptada.

## 7. Latencia objetivo

Objetivo operativo:

**≤ 10 minutos desde la recepción registrada hasta la validación automática o asignación formal a moderación.**

Este plazo es un objetivo, no una garantía.

La latencia real se medirá y formará parte de las métricas.

## 8. Moderadores

Los moderadores definitivos deberán identificarse por su función antes de T0.

Cuando sea posible, una apelación será revisada por una persona distinta de quien tomó la decisión inicial.

## 9. Apelación

Se permite una apelación por entrada.

Debe presentarse:

- dentro de las 24 horas posteriores al rechazo;
- y antes de DEADLINE_2.

La apelación puede:

- confirmar el rechazo;
- revocarlo y aceptar la contribución.

La decisión y su motivo quedan registrados.

## 10. DEADLINE_1

**DEADLINE_1 = T0 + 168 horas**

Después de DEADLINE_1 no se admiten nuevas contribuciones ni nuevas revelaciones.

## 11. DEADLINE_2

**DEADLINE_2 = T0 + 216 horas**

Esta ventana adicional existe únicamente para resolver moderaciones y apelaciones de entradas recibidas válidamente antes de DEADLINE_1.

Las entradas todavía pendientes al llegar DEADLINE_2 pasan a:

**EXCLUIDA**

de forma definitiva para la obra.

## 12. Privacidad

Las solicitudes de privacidad, oposición o supresión no son apelaciones de moderación.

Se gestionan mediante `PRIVACY.md` y pueden ejercerse independientemente de DEADLINE_1 y DEADLINE_2.

## 13. Manipulación de métricas

La existencia de múltiples identidades no se determinará automáticamente mediante sospechas o inferencias.

El sistema contabiliza nodos genealógicamente válidos y deja expresamente establecido:

**NODOS GENEALÓGICAMENTE VÁLIDOS ≠ IDENTIDADES ÚNICAS VERIFICADAS**

No se acusará públicamente a una persona de utilizar múltiples identidades sin evidencia suficiente.

## 14. Estado PRE-T0

Esta política permanece en borrador.

Antes de T0 deberán estar definidos y probados:

- moderadores;
- códigos de rechazo;
- procedimiento técnico;
- apelación;
- medición de latencia.

Las pruebas PRE-T0 se conservan como antecedentes y no forman parte de LEVIATÁN Ω. No se exige un piloto previo al lanzamiento.
