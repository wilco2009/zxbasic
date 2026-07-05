# Arquitectura `zx81sd`: ZX81 + SD81 Booster

`zx81sd` es una arquitectura de este compilador para un **ZX81 real con
la tarjeta [SD81 Booster](https://www.sd81.eu/)** (una interfaz que
añade pantalla tipo Spectrum, sonido AY/beeper, mapeador de memoria por
páginas y acceso a tarjeta SD).

Todo el código específico de esta arquitectura vive exclusivamente bajo:

```
src/arch/zx81sd/            (backend del compilador)
src/lib/arch/zx81sd/        (runtime ASM + stdlib BASIC)
```

## Regla de oro del port

Este compilador es compartido por todas las arquitecturas (zx48k,
zx128k, zxnext...). **El port de zx81sd nunca modifica el frontend ni
la stdlib/runtime compartidos.** El mecanismo de resolución de
`#include`/`#require` busca primero en `src/lib/arch/zx81sd/`, y si no
encuentra el fichero cae automáticamente en `src/lib/arch/zx48k/` (el
fichero compartido). Por eso muchos overrides de zx81sd son copias
completas de la versión zx48k con solo unas pocas líneas cambiadas: hay
que copiar el fichero entero, no un parche — un override parcial
simplemente no existe como concepto aquí.

Antes de tocar cualquier cosa fuera de `zx81sd/`, para: seguramente hay
una forma de resolverlo con un override.

## Estado del port

Funcionalmente completo desde 2026-07-02: FP (RST $28 propio),
gráficos (PLOT/DRAW/arcos/CIRCLE), sonido (BEEP y PLAY sobre AY ZonX y
beeper), teclado (INKEY$/INPUT sobre el teclado físico del ZX81),
joystick, la librería MCU completa (ficheros, RTC/BAT, voz, mapeador de
memoria...) y LOAD/SAVE/VERIFY...CODE contra SD.

Pendiente / sin auditar, resto de utilidades de pantalla de la stdlib
compartida:

- `winscroll.bas`: se cree ya portado y probado, pero sin confirmar con
  una auditoría formal (no hay override en `zx81sd/stdlib/` — de ser
  cierto, es porque no necesitaba ninguno, como `scroll.bas` antes del
  fix o `4inarow.bas`).
- `putchars.bas`/`puttile.bas`: sin auditar ni probar. Un vistazo rápido
  al fuente no encuentra direcciones de ROM/sysvars del Spectrum
  (`putChars` rellena un rectángulo de caracteres, `putTile` coloca un
  tile de 16×16 px), así que son buenos candidatos a funcionar sin
  cambios, pero no está confirmado.
- `screen.bas`: **sí depende de la ROM** (`$2538`/`$5C65`/`$19E8`,
  rutinas y sysvars fijas del Spectrum para leer de vuelta un carácter
  de pantalla) — necesitará un override real, no solo una auditoría.
- `print42.bas`/`print64.bas`: **portados** (override completo en
  `stdlib/`) — sysvars fijas → equivalentes zx81sd, y las constantes de
  base de pantalla/atributos se parchean en tiempo de ejecución
  (automodificación de código) en vez de ser fijas. Verificado por
  simulación (texto legible píxel a píxel, sin corrupción de memoria);
  pendiente de confirmar en el emulador/hardware real.

Ver [CAMBIOS_BASIC.md](CAMBIOS_BASIC.md) para el patrón general de este
tipo de fix. El port de `maskedsprites.bas`/MSFS (sprites enmascarados
sobre el mapeador de memoria) también está en proceso, aún sin terminar
de funcionar bien.

## Documentación

- **[USO.md](USO.md)** — cómo compilar un programa, empaquetarlo para
  el ZX81 y cargarlo desde la tarjeta SD.
- **[PRECAUCIONES.md](PRECAUCIONES.md)** — qué hay que tener en cuenta
  al escribir o portar software para esta arquitectura (mapa de
  memoria, sysvars, teclado, cosas que NO existen aquí aunque existan
  en Spectrum).
- **[CAMBIOS_BASIC.md](CAMBIOS_BASIC.md)** — qué cambios de fuente
  BASIC hizo falta para portar cada ejemplo oficial de `examples/` (con
  el porqué de cada uno). Punto de partida obligado antes de portar un
  ejemplo nuevo: casi siempre es uno de los patrones ya catalogados
  ahí.
- **[MAP.md](MAP.md)** — bitácora técnica detallada de todos los bugs
  encontrados y corregidos durante el port (runtime ASM, no fuentes
  BASIC), con la traza de investigación de cada uno. Es el documento a
  consultar cuando algo falla en tiempo de ejecución de forma que
  recuerda a un bug ya resuelto.

## Ejemplos

Los programas de ejemplo ya adaptados/probados para esta arquitectura
están en [`examples/sd81/`](../../examples/sd81/) (junto al resto de
`examples/` del compilador). El detalle de qué hubo que tocar en cada
uno, y por qué, está en [CAMBIOS_BASIC.md](CAMBIOS_BASIC.md).

## Herramientas de empaquetado y pruebas

El empaquetador (`split_sd81.py`, parte binario plano en páginas de
8KB + genera el cargador `.p` para el ZX81) y el conjunto más amplio de
fuentes de depuración/diagnóstico usados durante el desarrollo del port
viven en un repositorio complementario, no en este. Ver
[USO.md](USO.md) para el flujo completo de compilar → empaquetar →
cargar.

## Repositorios relacionados

- **[SD81 Booster](https://codeberg.org/Retrostuff/SD81-Booster)** —
  firmware/hardware de la interfaz para la que se ha hecho este port.
- **[EightyOne Cross-platform](https://codeberg.org/wilco2009/EightyOne-CrossPlatform)** —
  emulador usado durante el desarrollo para probar sin hardware real.
- **[CPM_SD81](https://codeberg.org/wilco2009/CPM_SD81)** — CP/M sobre
  el SD81 Booster.
