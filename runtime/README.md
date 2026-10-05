# Participación oficial

La herramienta del navegador prepara compromisos y revelaciones sin transmitir las futuras invitaciones. Los eventos originales de GitHub se capturan cifrados en almacenes privados separados. Una cola persistente procesa entradas por hora de recepción e ID, con escrituras atómicas del registro firmado y revalidación tras conflictos.

El adaptador autentica al autor de la revelación y al moderador. Nunca ejecuta contenido de aportaciones como código. La validación técnica no sustituye la moderación. Los eventos capturados pueden reintentarse; no se promete disponibilidad ilimitada del proveedor.

`python -m unittest discover -s tests -v` ejecuta pruebas técnicas con datos ficticios, excluidos del experimento. No constituyen un piloto ni una condición de participación.

`python -m runtime.audit` verifica documentos y firmas. La ejecución oficial exige `launch.json` en ACTIVE y aplica los plazos de servidor.
