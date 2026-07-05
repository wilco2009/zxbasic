# Precauciones al escribir o portar software para zx81sd

zx81sd hace que ZX BASIC genere binarios que "parecen" un Spectrum (la
interfaz SD81 Booster emula su pantalla, y buena parte de la stdlib
compartida asume convenciones del Spectrum), pero **no hay ROM del
Spectrum en ningún sitio**: no hay `RST $28` de la ROM, no hay rutinas
en direcciones fijas, no hay sysvars del Spectrum en `$5C00+`. Casi
todos los bugs de este port han venido de código (de examples/ oficiales
o de la stdlib compartida) que asume silenciosamente alguna de estas
cosas. Antes de portar algo, repasa esta lista.

## 1. Nunca hay ROM: cuidado con direcciones absolutas y sysvars

Cualquier `POKE`/`PEEK`/`CALL` a una dirección numérica fija
(23675, 23658, $22AC, $0DFE...) casi seguro que es una sysvar o rutina
de la **ROM del Spectrum**, que en zx81sd no existe: esa dirección cae
en RAM libre, o peor, en pleno código compilado del programa —
ejecutarla o interpretarla como dato produce corrupción silenciosa,
gráficos erróneos, o un `HALT`/reinicio salvaje muy difícil de
relacionar con la causa (varios bugs de este port tardaron sesiones
enteras en diagnosticarse por esto).

- **Sysvars del Spectrum → sysvars de zx81sd**: la tabla de
  equivalencias está en
  [`../../src/lib/arch/zx81sd/runtime/sysvars.asm`](../../src/lib/arch/zx81sd/runtime/sysvars.asm)
  (todas viven en `$8000+`, no en `$5C00+`). Ejemplos ya resueltos:
  `UDG` (23675 → `$8002`), `COORDS` (23677/23678 → `$8004`/`$8005`).
  Ver [CAMBIOS_BASIC.md](CAMBIOS_BASIC.md) para el detalle línea a
  línea de cada caso ya encontrado.
- **Rutinas de ROM llamadas directamente** (`call $22AC` = PIXEL-ADD,
  `call $0DFE` = CL-SC-ALL/scroll, `RST $28` = calculador FP...): si el
  fuente o una librería compartida hace esto, hace falta un override en
  `src/lib/arch/zx81sd/` que sustituya la llamada por la rutina propia
  con el **mismo contrato de registros** que la de la ROM (ver más
  abajo). Ejemplo resuelto: `stdlib/scroll.bas`.
- **`grep` preventivo**: al portar un fichero de `zx48k/` a `zx81sd/`,
  buscar `EQU 0[0-9A-F]` / `call 0x` / literales de 4-5 dígitos
  sospechosos antes de darlo por bueno, no solo cuando algo falla.

## 2. Contratos de registros de las rutinas ASM: son sagrados

Varias rutinas del runtime tienen contratos de preservación de
registros explícitos y no negociables porque el código que las llama
(heredado de zx48k, no tocable) depende de ellos al pie de la letra.
Ejemplos:

- `PIXEL_ADDR` (`runtime/pixel_addr.asm`): A=191, B=Y, C=X → HL=offset,
  A=X AND 7; **destruye B, preserva D y E**. `draw.asm` guarda la
  coordenada Bresenham en D alrededor de la llamada confiando en esto
  literalmente — romperlo (como pasó una vez con un intento que usaba D
  de scratch) corrompe cualquier línea con componente vertical sin
  tocar para nada las horizontales, lo que despista mucho a la hora de
  diagnosticar.
- `GetBankPreservingRegs`/`SetBankPreservingINTs` (MSFS,
  `cb/maskedsprites.bas`): contrato documentado "preserva D,E,H,L".
  Escribir el reemplazo en BASIC plano en vez de ASM a mano rompe esto
  sin ningún aviso del compilador (el código BASIC generado usa
  registros libremente por dentro) — un bug real de esta clase hizo que
  6 sprites de prueba se registraran todos en la misma dirección
  incorrecta. **Nota**: el port de MSFS/`maskedsprites.bas` sigue en
  proceso (aún no funciona del todo bien) — este ejemplo concreto sirve
  para ilustrar el tipo de bug, no como confirmación de que la librería
  ya esté terminada.

**Regla práctica**: si vas a sustituir una rutina ASM que tiene un
contrato de registros documentado (o que se puede inferir mirando quién
la llama y qué asume), reimplaza en ASM a mano preservando exactamente
ese contrato. Una función BASIC (`SUB`/`FUNCTION`), por sencilla que
parezca, NO es un reemplazo válido salvo que el contrato sea "ninguno".

## 3. El teclado es el del ZX81, no el del Spectrum

El SD81 Booster no tiene teclado Spectrum: reescanea el teclado físico
de 40 teclas del ZX81 (`runtime/io/keyboard/keyscan.asm`). Diferencias
que importan al portar/escribir código:

- Pulsación directa de una letra: minúscula. Con `SHIFT+letra`:
  MAYÚSCULA de esa letra — exactamente igual que en un Spectrum real, a
  diferencia del ZX81 original (donde `SHIFT+letra` daba un símbolo, no
  una mayúscula). Esta redefinición es una decisión de diseño de este
  port, ver [MAP.md](MAP.md) sección "Esquema de teclado nuevo". En
  consecuencia, **sí se puede escanear/comparar `INKEY$` contra
  mayúsculas de letra** (`IF INKEY$="S"`, pensado para jugarse con
  `SHIFT` sostenido al estilo Spectrum) sin ninguna limitación de
  hardware: basta con pulsar `SHIFT+S`.
- `SHIFT+"2"` alterna un CAPS LOCK persistente.
- `"."` es una tecla normal (`.` sin shift, `,` con shift). Los símbolos
  del ZX81 original asociados a cada tecla (`:` en Z, `)` en O, etc.) se
  alcanzan con la secuencia `"." + tecla` **solo desde `INPUT()`** (tecla
  muerta gestionada en `stdlib/input.bas`), no desde `INKEY$` a pelo —
  no hay forma de "sostener ambas a la vez" con fiabilidad en este
  teclado, así que la composición se hace pulsando `.` primero y la
  segunda tecla después. Pulsar `.` **dos veces seguidas** confirma el
  primer punto como literal y descarta cualquier combo: la tecla que
  venga después de ese segundo punto se lee como una pulsación nueva,
  sin combinar con nada (permite escribir cualquier tecla justo después
  de un punto sin arriesgarse a formar un símbolo por accidente).

## 4. No hay interrupciones: nunca esperes un `HALT`/`EI` para sincronizar

El runtime de zx81sd corre permanentemente con interrupciones
deshabilitadas (`DI`); el vector `$0038` es solo una trampa `DI;HALT`,
no un manejador de interrupción real. Cualquier código (típicamente
código ASM inline de un ejemplo, no de la stdlib) que haga `EI` seguido
de `HALT` esperando el pulso de 50Hz de la ROM del Spectrum **se cuelga
para siempre** — no hay nada que lo despierte.

- **Sustituto**: `VSYNC_TICK` (namespace `core`, en
  `runtime/vsync.asm`) sondea por puerto el contador de pulsos VSYNC
  real del hardware SD81 Booster. Ya lo usa `PAUSE` internamente.
- Al llamarlo desde un bloque `ASM ... END ASM` que no esté ya dentro de
  `push namespace core`, hay que usar el prefijo completo:
  `call .core.VSYNC_TICK` (si se omite el prefijo, el compilador da
  `Undefined GLOBAL label '.VSYNC_TICK'` — error ya visto más de una
  vez en este port).
- Un contador que antes se incrementaba solo por la interrupción en
  segundo plano (`FRAMES`/23672 en el Spectrum) hay que actualizarlo a
  mano llamando a `VSYNC_TICK` explícitamente en cada vuelta del bucle
  de espera, no solo una vez al principio.

## 5. Namespaces y mangling de etiquetas ASM

Un `DIM X` o `SUB`/`FUNCTION X` de BASIC se traduce a la etiqueta ASM
`_X` (un solo guion bajo), **salvo** que el fichero envuelva su código
en `push namespace core ... pop namespace`, en cuyo caso hay que
referenciarla desde fuera como `.core._X` (variables) o `.core.X`
(funciones/rutinas). Confundir esto en cualquier dirección produce
`Undefined GLOBAL label`. Si un fichero de este port no usa namespacing
en ningún otro sitio, no hace falta envolver un bloque `ASM` nuevo en
`push namespace core` solo porque otro fichero (como `vsync.asm`) sí lo
use — basta con prefijar la referencia puntual.

## 6. El eliminador de código muerto no ve las llamadas desde ASM a mano

El análisis de "¿esto se usa?" del compilador solo cuenta llamadas
hechas con sintaxis BASIC (`Foo(x)`). Una `SUB`/`FUNCTION`/variable
BASIC referenciada **solo** desde un bloque `ASM ... END ASM` (p. ej.
`call _Foo`) puede ser eliminada como código muerto, dando
`Undefined GLOBAL label '._Foo'` al enlazar — el símbolo nunca llegó a
existir en el binario final. Dos salidas:

- Si es un dato puro (un byte de estado, por ejemplo), declararlo como
  ASM puro (`ASM \n _Label: \n DEFB 0 \n END ASM` a nivel de fichero),
  no como `DIM`.
- Si es una función que de verdad hace falta que sea BASIC (porque
  llama a otras cosas de la stdlib), añadir una llamada BASIC real
  (aunque sea redundante/no estrictamente necesaria en ese punto) en
  algún sitio alcanzable del código, para que el análisis de uso la
  cuente.

## 7. Metodología de depuración sin hardware

Para diagnosticar sin gastar ciclos de prueba-error en el emulador o el
hardware real, este port usa simulación directa del binario con el
paquete `z80` de Python. Dos lecciones ya aprendidas por las malas
(documentadas con más detalle en [MAP.md](MAP.md)):

- Comprobar el PC periódicamente cada N ticks gruesos puede dar falsos
  "atascado" si justo cae siempre en el mismo punto de un bucle; usar
  breakpoints reales (comparar `m.pc` contra la dirección exacta,
  sacada del `.map`) o chunks de tick más finos.
- La RAM del simulador nace a **ceros**, igual que la del Spectrum tras
  el test de RAM de su ROM. Esto oculta bugs de memoria no inicializada
  (dio dos falsos "OK" seguidos en el bug del free-space-bitmap de
  MSFS). Para validar código que lee memoria que no inicializa él
  mismo, rellenar toda la RAM no cargada con `0xFF` antes de cargar el
  binario, para reproducir las condiciones reales de hardware/tarjeta.
- El simulador **no modela el mapeador de memoria** (`OUT` al puerto
  `$E7` es un no-op): puede validar que la lógica Z80 es autoconsistente,
  pero no que el intercambio de página físico funcione de verdad — eso
  solo se confirma en el emulador (EightyOne) o en hardware real.
- Si un binario falla en EightyOne pero la simulación Python lo ejecuta
  limpio, sospecha primero del emulador (ver el bug de traps de cinta ya
  encontrado y corregido en `Eightyone2/src/ZX81/rompatch.cpp`, en el
  repositorio del emulador, no en este) antes que del runtime — en
  hardware real esos traps no existen.

## 8. Nunca hagas `#include once <sysvars.asm>` desde una librería propia

Si necesitas los sysvars propios de zx81sd (`CHARS`/`UDG`/`ATTR_P`/
`SCREEN_ADDR`/`SCREEN_ATTR_ADDR`...) desde un fichero `stdlib/*.bas`
nuevo, **no lo incluyas tú mismo con `#include once <sysvars.asm>`** —
solo referencia los símbolos con el prefijo `.core.` (ver punto 5) y
confía en que el resto del runtime ya lo trajo.

`sysvars.asm` arrastra tras de sí `bootstrap.asm` → `charset.asm`, y
este último hace `INCBIN "specfont.bin"` (el font completo, bytes
binarios, no texto ensamblador). Si tu fichero resulta ser el
**primero** en incluir `sysvars.asm` en todo el programa compilado
(fácil que pase: un `#include <tulibreria.bas>` al principio del fuente
del usuario se procesa antes que cualquier `CLS`/`PRINT` textualmente
posterior), ese `INCBIN` se emite **justo en el punto del fichero fuente
donde pusiste el `#include`**:

- Puesto a nivel BASIC (fuera de un bloque `ASM ... END ASM`): el lexer
  de BASIC intenta tokenizar esos bytes binarios como si fueran texto
  fuente → `error: illegal preprocessor character` en líneas que no
  tienen nada que ver con el problema real (mal atribuidas al inicio
  del fichero).
- Puesto dentro de un bloque `ASM` (p. ej. al principio del cuerpo de
  una función): el binario del font se emite literalmente en medio del
  código compilado de esa función — compila sin error, pero la CPU
  "ejecuta" esos bytes de font como si fueran instrucciones en cuanto
  el flujo de control cae ahí, produciendo un `HALT` o comportamiento
  errático en una dirección que no tiene relación aparente con el bug
  (encontrado al portar `print42.bas`/`print64.bas`, ver
  [CAMBIOS_BASIC.md](CAMBIOS_BASIC.md)).

Cualquier programa real que use tu librería casi seguro que también usa
`CLS`/`PRINT` en algún punto, y esas rutinas ya requieren `sysvars.asm`
— así que omitir el `#include` en tu fichero es seguro en la práctica,
no una chapuza.

## Ver también

- [CAMBIOS_BASIC.md](CAMBIOS_BASIC.md) — catálogo de cambios de fuente
  ya necesarios en ejemplos oficiales, con el patrón general a buscar
  en cualquier ejemplo nuevo.
- [MAP.md](MAP.md) — bitácora técnica completa, bug a bug, con las
  trazas de investigación.
