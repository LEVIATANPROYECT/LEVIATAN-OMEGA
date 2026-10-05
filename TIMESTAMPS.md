# Sellado temporal

El manifiesto y el génesis tienen pruebas OpenTimestamps adjuntas (`.ots`). Los calendarios gratuitos aceptaron sus compromisos antes de activar T0. La recepción de un calendario está **pendiente de confirmación en Bitcoin**; no se presenta como confirmación ya verificada.

El flujo `Periodic public timestamp` comprueba cada media hora si corresponde guardar un nuevo estado firmado por cada intervalo de seis horas desde T0. La programación de GitHub puede retrasarse. Cada prueba conserva exactamente el archivo al que corresponde en `timestamps/`; no se sustituye por una versión posterior del registro.

Un hash prueba integridad, no una fecha por sí solo. Las fechas de GitHub son referencias del proveedor; las pruebas `.ots` deben actualizarse y verificarse independientemente cuando los calendarios dispongan de las atestaciones correspondientes.

Herramienta y documentación de verificación: [OpenTimestamps](https://opentimestamps.org/) y [cliente oficial](https://github.com/opentimestamps/opentimestamps-client).
