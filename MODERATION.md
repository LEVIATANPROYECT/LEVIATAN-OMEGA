# LEVIATÁN Ω — Política de moderación

**VERSIÓN DEFINITIVA 1.0**

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

Responsable de moderación: Pedro Rivilla (Peter), mediante la cuenta LEVIATANPROYECT. Puede utilizar asistencia de IA bajo sus instrucciones, también para ejecutar decisiones conforme a estos criterios. No se presenta a la IA como una persona ni como un revisor independiente.

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

## 14. Procedimiento técnico

La validación técnica consume la invitación y deja la contribución PENDIENTE_MODERACIÓN. El responsable publica en el issue de revelación un comando JSON con el prefijo `LEVIATAN-OMEGA/1`, seguido de una nueva línea:

`{"kind":"accept","version":1,"reason":"VALID"}`

o `{"kind":"reject","version":1,"reason":"IRRELEVANT"}`.

Los códigos de rechazo son IRRELEVANT, SPAM, RIGHTS, PRIVACY, ILLEGAL, MANIPULATION y CONDITIONS. Solo la cuenta del responsable puede moderar. La justificación adicional debe ser proporcionada y no divulgar información personal innecesaria.

La apelación se presenta desde la cuenta autora como comentario en el mismo issue, con el mismo prefijo y nueva línea:

`{"kind":"appeal","version":1}`

El estado pasa a APELACIÓN_PENDIENTE; se aplica el plazo de 24 horas y el cierre final. Una apelación puede incluir por separado una explicación pública sin datos sensibles, o enviarse al contacto oficial. Un nuevo envío no sustituye la captura original.

Las retiradas se gestionan conforme a PRIVACY.md. Los fallos y retrasos se registran; el objetivo de diez minutos no es una garantía de disponibilidad. No se exige un piloto para lanzar.
