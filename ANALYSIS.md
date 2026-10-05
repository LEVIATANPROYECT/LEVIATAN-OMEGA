# LEVIATÁN Ω — Plan de análisis prerregistrado

Versión 1.0. Se fija y firma antes de T0. No hay umbral de éxito esperado.

## Población, ventanas y unidades

Se incluye cada revelación técnicamente válida recibida desde T0 inclusive hasta T0 + 168 horas exclusive, cuyo compromiso original se recibió dentro de esa ventana y menos de 24 horas antes. Se resuelve moderación y apelación hasta T0 + 216 horas exclusive. La unidad es un nodo genealógico, no una persona única verificada. Ω₀ es el génesis y no cuenta como aportación de un participante.

Se excluyen del resultado oficial todos los antecedentes PRE-T0, pruebas de desarrollo, eventos inválidos y duplicados. Los fallos de captura se documentan como incidencias; nunca se rellenan con participantes estimados. La recepción procede del evento original de GitHub y el procesamiento conserva su tiempo aparte.

## Métricas principales

- **CONTRIBUCIONES_ACEPTADAS:** nodos con estado ACEPTADA en el corte, excluido Ω₀. Las retiradas se informan por separado.
- **TRANSFORMACIONES:** nodos aceptados con `derives_from` válido o tipo «Transformación de contribución anterior». Es una clasificación declarada, no una medida automática de calidad o distancia semántica.

## Métricas secundarias

- **EMBUDO:** compromisos capturados, revelaciones capturadas, revelaciones técnicamente válidas, aceptaciones, rechazos, apelaciones, exclusiones y retiradas. Se calcula desde recibos privados y se publica agregado. Un reintento del mismo evento cuenta una vez.
- **PROPAGATORS:** nodos aceptados o retirados con al menos un hijo genealógicamente válido; Ω₀ se informa separadamente.
- **VALID_GENEALOGICAL_NODES:** revelaciones que superaron validación técnica y consumieron token, desglosadas por estado de moderación.
- **RETIRADOS:** nodos RETIRADA; sus hijos no se invalidan automáticamente.
- **LATENCIAS:** recepción a validación y recepción a primera moderación; mediana, percentil 95 mediante rango más próximo y máximo, en segundos. Ausencias se indican pendientes, sin imputar valores.
- **REACHED_ESTIMATED:** no se calcula salvo datos declarados de difusión; cualquier estimación futura se separará como exploratoria y no verificada.

## Generaciones y cocientes

Vg es el número de nodos genealógicamente válidos de generación g. Pg es el número de nodos de g con al menos un hijo válido. V0 = 1 para el génesis.

- R_total(g) = Vg / V(g−1).
- R_prop(g) = Vg / P(g−1).

Un denominador cero produce «no definido». No se confunden estos cocientes con reproducción poblacional de personas. Una rama detenida y cero aportaciones son resultados válidos.

## Corte final y limitaciones

Las moderaciones pendientes al cierre final pasan a EXCLUIDA. Se publica estado final, hashes, firma, certificación e incidencias conocidas. Los derechos de privacidad siguen vigentes. La fecha del corte se diferencia de la de producción del informe.

No se realizan inferencias causales ni de representatividad: reclutamiento voluntario mediante invitaciones y contactos elegidos por el creador, sin grupo de control ni verificación de unicidad humana. Cualquier análisis no definido aquí llevará la etiqueta «exploratorio».
