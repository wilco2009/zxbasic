# Mapa de tests de depuración (sesión DRAW3 / arco)

Nota sobre rutas: esta bitácora se escribió originalmente en el
repositorio complementario de pruebas del port (donde los `.bas` citados
vivían todos en un directorio `tests_debug/`). Los ejemplos que se
consideraron suficientemente maduros para publicarse ya están copiados
en este repositorio, en [`examples/sd81/`](../../examples/sd81/)
(`flights_sd81.bas`, `snake_sd81.bas`, `maskedsprites_sd81.bas`,
`pong.bas`, `block7test.bas` — ver [CAMBIOS_BASIC.md](CAMBIOS_BASIC.md)).
El resto de fuentes de depuración puntual mencionadas aquí (`diag1-6`,
`t_arc*`, `trig_test`, `heaptest`, `keytest`...) siguen solo en el
repositorio complementario, no en este.

Compilación de cada uno (desde la raíz de este repositorio):
```
python -m src.zxbc.zxbc examples\sd81\<nombre>.bas --arch zx81sd -o <nombre>.bin
python split_sd81.py <nombre>.bin <PREFIJO>
```
(`split_sd81.py` vive en el repositorio complementario — ver [USO.md](USO.md).)

| Fuente                | Prefijo SD81 | Qué prueba                                                        | Resultado obtenido |
|------------------------|--------------|---------------------------------------------------------------------|---------------------|
| `str_test.bas`         | STRTEST      | PRINT/STR$ de FLOAT (Fase 3)                                        | OK: 7 / 7.5 / -3.25 / 0 / 123.5 / -0.5 |
| `trig_test.bas`        | TRIGTST      | SQR/SIN/COS/EXP/LN/ATN con argumentos triviales (Fase 4)             | OK: 3 / 1.41421 / 0 / 1 / 2.71828 / 1 / 3.14159 |
| `trig2_test.bas`       | TRIG2        | SIN/COS con argumentos NO triviales (1, 1.5708, 3.14159)             | OK: 0.8147(4?) / 0.5403 / 0.99999 / -0.99999 / 0 |
| `draw_arc_test.bas`    | DRAWARC      | DRAW+DRAW+CIRCLE combinados (primer intento de arco)                 | Solo aparece una línea vertical, CIRCLE nunca se ve |
| `t_line.bas`           | TLINE        | `DRAW 20,0` (2 args, sin ángulo, sin FP)                             | OK: línea horizontal |
| `t_circle.bas`         | TCIRC        | `CIRCLE 60,30,20` sola                                               | OK: círculo correcto |
| `t_arc.bas`            | TARC         | `DRAW 20,0,3.14159` (arco solo, offset horizontal, 180°)              | BUG: línea vertical (no horizontal, no arco) |
| `t_arc2.bas`           | TARC2        | `DRAW 30,10,1.5708` (offsets asimétricos, 90°)                       | BUG: línea vertical con leve inclinación a la derecha |
| `t_arc3.bas`           | TARC3        | `PLOT 100,96` + `DRAW 20,0,3.14159` (centrado, con margen)            | BUG: patrón de varias líneas en estrella/caóticas desde el centro; una se sale de pantalla hacia el área de atributos |
| `diag1.bas`            | DIAG1        | ASM inline: llama a CD-PRMS1 (L247D) directamente con z=40, A=pi/2, e imprime mem-1/mem-3/mem-4/mem-0/nº de líneas | Pantalla en blanco — bug del propio test (`#include` dentro de `ASM` mete código ejecutable en el flujo lineal). Sustituido por diag2 |
| `diag2.bas`            | DIAG2        | Igual que diag1 pero sin includes manuales: variables BASIC + PRINT normal | OK: valores exactos esperados → CD-PRMS1 numéricamente correcto |
| `diag4.bas`            | DIAG4        | Con `-D DRAW3_DEBUG`: imprime solo N (nº de segmentos capturados en el hook de draw3.asm) | OK: 16 → el hook de captura funciona |
| `diag5.bas`            | DIAG5        | diag4 + bucle de recorrido del buffer (2 páginas SD81)               | No imprimía; descartado, sustituido por diag6 (1 página) |
| `diag6.bas`            | DIAG6/DIAG7  | diag4 + bucle, 1 página. Su volcado de $152D + breakpoints de escritura en $8004 localizaron el bug | OK: 16/16. DIAG7 = idéntico recompilado tras el fix |
| `arcfix.bas`           | ARCFIX       | Test de referencia idéntico al Spectrum real: `PLOT 100,100` + 2 DRAW arco + CIRCLE | **OK tras el fix**: gancho + círculo, igual que la foto del Spectrum real |

## Bug de DRAW3 (arco) — RESUELTO

**Causa raíz** (nada que ver con el calculador FP, cuya matemática resultó
ser exacta): `src/lib/arch/zx81sd/runtime/pixel_addr.asm` destruía el
registro **D** (lo usaba como scratch para V=191−Y). Pero `draw.asm`
(heredado de zx48k) salva la coordenada Y del Bresenham en D' alrededor de
la llamada (`ld d,b / call PIXEL_ADDR / ld b,d`), porque PIXEL-ADD ($22AC)
de la ROM Spectrum preserva DE. Resultado: cada línea con componente
vertical arrancaba internamente con Y=191−y1, corrompiendo COORDS y el
trazado. Las líneas horizontales (t_line) y CIRCLE (que no pasa por ese
camino) salían bien, lo que despistó la investigación inicial.

**Fix**: PIXEL_ADDR reescrito para usar B como scratch (ya se destruía,
igual que en la ROM) y preservar D y E. Verificado en hardware con ARCFIX
(idéntico al resultado del Spectrum real) y DIAG7.

**Método de localización**: hook `#ifdef DRAW3_DEBUG` en draw3.asm (activado
con `-D DRAW3_DEBUG`) que captura por cada segmento: |Dy|,|Dx|,signos y
COORDS previas en un buffer (`DRAW3_DEBUG_BUF`); volcado de memoria del
buffer en el debugger de EightyOne + breakpoints de escritura en COORDS
($8004/$8005). El volcado demostró que la posición FP acumulada era
perfecta y que COORDS quedaba mal tras cada línea → el bug estaba en
__DRAW/PIXEL_ADDR, no en fp_calc.asm ni draw3.asm.

## Ficheros fuente modificados/creados en esta sesión (motor FP + arco)

- `src/lib/arch/zx81sd/runtime/fp_calc.asm` — Fases 1-5 (motor CALCULATE,
  trig/log/exp/sqrt, y ahora STK-TO-A/STK-TO-BC/CD-PRMS1 para el arco).
  También se le añadió `#include once <stackf.asm>` (bug independiente:
  se incluye siempre en todo binario zx81sd, así que debía bastarse a
  sí mismo).
- `src/lib/arch/zx81sd/runtime/draw3.asm` — NUEVO. Override de
  `zx48k/runtime/draw3.asm` que sustituye las llamadas a direcciones
  ROM fijas por las rutinas portadas en `fp_calc.asm`. Incluye
  instrumentación de traza tras `#ifdef DRAW3_DEBUG` (inactiva por
  defecto; se activa compilando con `-D DRAW3_DEBUG`).
- `src/lib/arch/zx81sd/runtime/pixel_addr.asm` — FIX del bug del arco:
  ahora preserva D y E (antes destruía D, rompiendo el Bresenham de
  draw.asm en toda línea no horizontal).
- `src/lib/arch/zx81sd/runtime/fp_tostr.asm`, `printf.asm`, `str.asm` —
  de la Fase 3 (PRINT/STR$ de FLOAT), sin cambios en esta sesión.

## Sonido: BEEP y PLAY (chips AY ZonX del SD81)

| Fuente          | Prefijo SD81 | Qué prueba                                              | Resultado |
|-----------------|--------------|----------------------------------------------------------|-----------|
| `beeptest.bas`  | BEEPTS2      | BEEP variable (runtime FP) + BEEP constante (corrección de reloj 13/14 en __BEEPER) | OK: escala + DO/DO' + LA 440 |
| `playtest.bas`  | PLAYTS2      | PLAY 3 canales + comparación AY/beeper                   | OK (¡ojo: notas en minúscula = octava abajo!) |
| `aycal.bas`     | AYCAL        | Emparejamiento AY vs beeper por semitonos                | Sirvió para detectar el desfase |
| `aycal2.bas`    | AYCAL2       | Duraciones cronometrables + pareja directa               | FFT: beeper 434.5 (correcto, pacing emulador), AY 220 |
| `aycal3.bas`    | AYCAL3       | Igual con notas en MAYÚSCULA                             | OK: unísono 440/440 |

Lección de la investigación de la "octava fantasma": en el MML de PLAY
(semántica del BASIC 128K), las notas en MINÚSCULA suenan una octava por
debajo de la octava actual. Los tests iniciales usaban minúsculas y el AY
sonaba a 220 Hz *por diseño*. El emulador, la tabla de divisores
(1.625 MHz) y el beeper (3.25 MHz) eran correctos. Se verificó con FFT
sobre la salida de audio grabada. De regalo se corrigió un bug latente
real de EightyOne (el reloj del AY quedaba con el de la tarjeta del
diálogo de hardware en vez del ZonX forzado por el SD81: faltaba llamar a
Sound.InitDevices() tras forzar machine.aytype).

## Librería MCU (SD81 Booster) — `zx81sd/stdlib/mcu.bas` + `joy.bas`

| Fuente         | Prefijo SD81 | Qué prueba                                                | Resultado |
|----------------|--------------|------------------------------------------------------------|-----------|
| `joytest.bas`  | JOYTS2       | `Joy("QAOPM")` (cmd 21) + validación local + eco INKEY$     | OK |
| `mcutest.bas`  | MCUTST       | VERSION, GET/SETBYTE, PWD, SAVE+LOAD+verificación, DEL, FREE, RTC, BAT, DIR, AY2 por registros, AyPlay | pendiente |
| `maptest.bas`  | MAPTST       | `Map(bloque,pagina)`/`MapGet` — mapeador $E7: firmas en 2 páginas conmutando el bloque 5 y verificación | OK |
| `exttest.bas`  | EXTTST       | Extensiones no-MCU: `HexPoke` (*HEX), `MemMove` (*LDIR/*LDDR, stdlib), `StrInv`/`StrBold` (*INV/*BOLD) | OK |
| `ftest.bas`    | FTEST        | Handles F_*: SAVE, F_OPEN_ZX81 (cmd 58), F_SEEK, F_READ con verificación, F_WRITE+relectura, F_CLOSE, DEL | OK |
| `lstest.bas`   | LSTEST       | Statements LOAD/SAVE/VERIFY ... CODE nativos → SD (override runtime load.asm/save.asm, cmd 9/10): SAVE+LOAD+verificación, VERIFY ok/corrupto (ERR 26), fichero inexistente (ERR 26) | OK |

Arquitectura: `mcu.bas` contiene las primitivas del protocolo en ASM
(McuSend/McuRecv/McuSendBlock/McuRecvBlock — las *Block son el camino
crítico de LOAD/SAVE/F_READ/F_WRITE) y los wrappers de todos los
comandos del manual (sistema, ficheros, handles F_*, hardware, voz,
AY2/VGM/PEG, RTC/BAT). Conversión ASCII↔ZX81 automática en los comandos
de texto. `joy.bas` es una capa fina sobre `mcu.bas`.

Notas de protocolo (extraídas de SD81Booster.cpp del emulador):
- Tras CADA operación en $A7 se espera el cambio del bit 7 de $AF.
  NUNCA escribir en $AF (reset del MCU).
- Strings Z80→MCU: byte de longitud + datos (el MCU convierte ZX81→ASCII
  salvo comandos "raw": JOY, BINARY_SAY, F_OPEN).
- Streams MCU→Z80 (PWD/DIR/TYPE/FREE_TXT): pedir cada carácter
  escribiendo CMD_NEXTCH ($0D); fin = EOT ($6F); después llega el status.
- Respuestas de longitud fija (LOAD, FREE, RTC, BAT, F_READ): ráfaga
  de bytes leyendo $A7 con espera de reloj entre cada uno.
- F_OPEN: confirmado en el firmware (COMMANDS.cpp) que el MCU asigna el
  handle y lo devuelve (el manual estaba mal y se ha corregido). Añadido
  F_OPEN_ZX81 (58) a la librería y al emulador.
- OPENDIR/GETROWLEN/GETROW (16-18) no están emulados en EightyOne:
  probarlos solo en hardware real.

## Test de integración: comecoquitos.bas (ejemplo oficial de zxbasic)

| Fuente | Prefijo SD81 | Qué prueba | Resultado |
|---|---|---|---|
| `examples/english/comecoquitos.bas` | COMECO | Juego completo de 1985: FP, strings/slices, arrays, UDGs, bloques gráficos, color/FLASH/BRIGHT, INKEY$, BEEP, RND | OK — idéntico al .tap de Spectrum |
| `fpleak.bas` | FPLEAK | Detector de fugas de la pila FP por bloques (lee $8024 tras cada idiom) | Sirvió para acotar; la "fuga" era corrupción por UDGs |
| `blocktest.bas` | BLKTST | Los 16 gráficos de bloque CHR$(128)-143 | OK tras el fix de PO_GR_1 |

Tres bugs del runtime cazados con este juego (commits 9903c866 y 9a24059e):
1. UDG apuntaba 128 bytes más allá del final de la fuente (96 chars, no
   256): los POKE USR CHR$ machacaban código del runtime → cuelgue en el
   primer uso del calculador. Fix: área dedicada de 21 UDGs.
2. INKEY$ devolvía mayúsculas; el modo L del Spectrum (y los programas de
   la época) usan minúsculas. Fix: tabla de keyscan en minúscula.
3. PO_GR_1 (bloques CHR$(128)-143) generaba patrones corruptos (OR al
   registro equivocado + cuadrantes izq/der invertidos). Fix: algoritmo
   literal de la ROM.

RECETA para ejemplos clásicos transcritos de Sinclair BASIC: compilar con
`--string-base 1 --array-base 1` (indexación 1-based). Sin ello, las
colisiones por slicing de strings salen desplazadas una posición (no es
un bug del port: en zx48k pasa igual).

## Heap en $8100 + traps de cinta de EightyOne — RESUELTO (2026-07-04)

| Fuente | Prefijo SD81 | Qué prueba | Resultado |
|---|---|---|---|
| `tests_debug/heaptest.bas` | HEAPA..HEAPE | Gestor de memoria dinámica (3 fases: crecimiento char a char, REALLOC grandes, STR$ en bucle) con el heap en distintas direcciones | Bisección que aisló el bug |
| `tests_debug/memtest.bas` | MEMTST | R/W patrón dependiente de dirección en $8100-$BFFF (2 pasadas) | OK — descartó el hardware/paginación |
| `tests_debug/inputtest.bas` | INTEST | INPUT() mínimo aislado | Reproducía el cuelgue |
| `examples/sd81/flights_sd81.bas` | FLIGHT | Simulador de vuelo: PEEK COORDS ($8004/5), FP intensivo, INPUT | Adaptación de examples/flights.bas |

Dos bugs encadenados, cazados el 2026-07-04:

1. **Compilador (`src/arch/zx81sd/backend/main.py`)**: `heap_size`/`heap_address`
   se registraban con `ADD_IF_NOT_DEFINED`, pero el backend Z80 genérico ya
   las define antes (4768 / None) → los valores zx81sd ($8100 / 16127) nunca
   se aplicaban y el heap acababa inline (DEFS) dentro de la zona ejecutable,
   desperdiciando 4768 bytes y limitando el heap. Fix: asignación directa
   `OPTIONS.heap_size/heap_address` (la CLI puede seguir sobreescribiendo).

2. **Emulador (`Eightyone2/src/ZX81/rompatch.cpp`, `PatchTest`)**: los traps
   de cinta de la ROM ZX81 ($0207/$02FF/$031E/$0356) se disparaban comparando
   PC + `memory[pc]` **plano**, que conserva la ROM aunque el SD81 tenga RAM
   mapeada. Con el heap en EQU el runtime baja $12A0 bytes y la división
   __DIVU16_FAST aterrizaba en $02FF → el trap de SAVE hacía `DE=1` en mitad
   de la división → cociente basura estable → bucle infinito de dígitos en
   __PRINTU_LOOP (PUSH AF sin pop) → la pila descendía arrasando el runtime.
   Los builds con heap inline eran inmunes de casualidad: las 4 direcciones
   trampa caían dentro del bloque DEFS (datos, el PC nunca pasa por ahí).
   Fix: `PatchTest` lee el byte con `zx81_PatchPeek()` (mapper-aware).
   En hardware real este bug NO existe (no hay traps).

Metodología que lo resolvió: simulación determinista del binario con la
librería Python `z80` (pip install z80) — diff de integridad de la zona de
código tras cada tramo + breakpoints comparando registros con EightyOne.
El binario era correcto en Z80 puro → la divergencia estaba en el emulador.
Arnés en el scratchpad de la sesión (runsim*.py, reproducible).

## Scroll de PRINT saltaba a la ROM del Spectrum — RESUELTO (2026-07-04)

Tercer bug de la cadena de flights.bas (viento=10, dir=100 → HALT): el
`print.asm` de zx81sd conservaba del zx48k el fallback
`__SCROLL_SCR EQU 0DFEh` (rutina CL-SC-ALL de la ROM del Spectrum). En
zx81sd no hay ROM: el primer PRINT que desbordaba la pantalla hacía CALL
a la línea BASIC compilada que casualmente ocupara $0DFE → ejecución
salvaje → RETURN de gosub sacando basura → HALT. Dependía de la entrada
porque el nº de dígitos tecleados movía el cursor: con viento "1"/"0" el
texto no llegaba a desbordar; con "10"/"100" sí. Ningún test anterior lo
pilló porque todos usan PRINT AT (nunca scroll).

Fix: la implementación por búfer (`__ZXB_ENABLE_BUFFER_SCROLL`, scrollea
vía SCREEN_ADDR/SCREEN_ATTR_ADDR) es ahora la rama única de __SCROLL_SCR
en zx81sd/runtime/print.asm. Verificado con el simulador Python + teclado
scriptado: el bucle principal del juego mantiene SP estable durante miles
de pasos. Ojo futuro: revisar cualquier otro EQU/CALL a direcciones
absolutas de ROM Spectrum al portar ficheros del zx48k (grep hecho:
no queda ninguno en el runtime zx81sd).

## Esquema de teclado nuevo: mayúsculas, CAPS LOCK y símbolos — 2026-07-04

| Fuente | Prefijo SD81 | Qué prueba | Resultado |
|---|---|---|---|
| `tests_debug/keytest.bas` | KEYTST | INKEY$ interactivo: imprime código ASCII + carácter de cada tecla | Verificado por simulación exhaustiva (ver abajo); pendiente de probar a mano en el emulador/hardware |

El teclado físico del ZX81 no distingue mayúscula/minúscula por tecla
(ver [[zx81sd-keyboard-case]]): SHIFT+letra da un símbolo, no la
mayúscula de esa letra. Hasta ahora `keyscan.asm` solo devolvía
minúsculas siempre. Nuevo esquema (`src/lib/arch/zx81sd/runtime/io/
keyboard/keyscan.asm`, reescrito de raíz):

- Sin modificador: minúscula (igual que antes — comecoquitos, snake,
  flights, row4 siguen funcionando sin tocar una línea, porque ninguno
  usa SHIFT).
- `SHIFT + letra`: MAYÚSCULA de esa letra.
- `SHIFT + "2"`: conmuta CAPS LOCK persistente (mudo, no imprime nada).
- CAPS LOCK activo: minúscula pasa a mayúscula; SHIFT sigue dando
  mayúscula igual (es un OR, no hay interacción, decisión tomada con el
  usuario).
- `"."` sola: `.`
- `SHIFT + "."`: `,` (igual que en el ZX81 real).
- `"." + otra tecla`: el símbolo impreso en el teclado del ZX81 para esa
  tecla (`:` con Z, `)` con O, RUBOUT con 0, etc. — la vieja tabla SHIFT
  del ZX81, ahora alcanzable con "." en vez de con SHIFT, ya que SHIFT
  se ha redefinido para dar mayúsculas).

Requirió reescribir el escaneo: antes se paraba en la primera fila con
algo pulsado (bastaba con una tecla a la vez). Ahora hacen falta dos
lecturas de puerto dedicadas para SHIFT (fila 0) y "." (fila 7, columna
1), más un escaneo de las demás filas buscando una tercera tecla
excluyendo esas dos posiciones (rutina `FIND_OTHER`). El combo
`SHIFT+"2"` usa un byte de estado persistente con detección de flanco
para no conmutar varias veces mientras se mantiene pulsado.

Verificado con un arnés de simulación Python (`z80`, ver metodología ya
usada para los bugs del heap): se llama a `__ZX81SD_KEYSCAN` directamente
inyectando por el callback de E/S los bits de fila exactos de cada
combinación (Z sola, SHIFT+Z, "."+Z, SHIFT+2 mantenido 4 polls seguidos,
etc.), sin pasar por la complejidad de un teclado real. Los offsets de
las tablas y del estado (`_KBD_*`, todos LOCAL al PROC, no aparecen en el
`.map`) se localizaron buscando el patrón de bytes de `UNSHIFT_TABLE`
("zxcvasdfg") en el binario y calculando el resto por desplazamiento fijo
(cada tabla ocupa 39 bytes). Los 12 casos de la tabla de diseño
coincidieron exactamente, incluido el debounce del CAPS LOCK.

### Corrección 2026-07-04: el modificador "." se movió de keyscan a input.bas

Al probarlo en el emulador, el usuario detectó que `"."+tecla` (pensado
para dar el símbolo del ZX81 pulsando ambas a la vez, como SHIFT+letra)
era impracticable desde `INPUT`: `PRIVATEInputWaitKey` compromete la
tecla `"."` en cuanto la detecta sola, sin dar tiempo a que la segunda
tecla llegue de verdad a la vez (a diferencia de SHIFT+letra, que sí se
puede sostener cómodamente con la otra mano). Diagnóstico correcto del
usuario: *"la gestión de los símbolos no debe ir en el keyscan sino en
INPUT.bas"*.

Fix: `keyscan.asm` ahora trata `"."` como una tecla más — sin
modificador da `.`, con SHIFT da `,` (igual que el ZX81 real), sin
ninguna lógica de "tercera tecla" para el punto (se quitó por completo
la exclusión de la fila 7 en `FIND_OTHER`, ya no hace falta). Las tablas
`UNSHIFT_TABLE`/`SYMBOL_TABLE`/`CAPS_TABLE` se promovieron de `LOCAL` a
ámbito de fichero (prefijo `__ZX81SD_`) y se añadió una rutina nueva,
`__ZX81SD_SYMBOL_FOR(char)`, que hace la búsqueda inversa
UNSHIFT_TABLE→SYMBOL_TABLE dado un carácter ya decodificado.

La composición de símbolos ahora vive en `stdlib/input.bas` como una
"tecla muerta" secuencial: al leer `"."`, la función `input()` lee la
SIGUIENTE tecla por separado (sin exigir simultaneidad) y llama a
`PRIVATEInputSymbolFor()`; si hay símbolo, lo añade; si no, añade el
punto literal y procesa la segunda tecla con normalidad (DEL, ENTER, o
un carácter más).

Bug propio cazado durante la implementación (antes de que el usuario lo
viera): `"."` + `"0"` resuelve a RUBOUT (12) vía `SYMBOL_TABLE` (es el
símbolo real que el ZX81 imprime sobre la tecla "0"), lo que borraría el
carácter anterior al escribir cualquier decimal terminado en ".0" (muy
habitual: "3.0", "10.0"...). Se excluyó ese valor explícitamente en
`input.bas` — RUBOUT ya se alcanza sin ambigüedad con SHIFT+0 (sí es
cómodo de sostener a la vez). Verificado con simulación de programa
completo (tecleo scriptado "1",".","0",ENTER → `a$="1.0"` correctamente,
y "."," o",ENTER → `a$=")"`), no solo con la función aislada.

`tests_debug/keytest.bas` (KEYTST) sigue siendo el tester interactivo de
`INKEY$`; `tests_debug/inputtest.bas` (INTEST) es el mismo mini test de
`INPUT()` de antes, ahora también sirve para probar la composición de
símbolos a mano.

### Refinamiento 2026-07-04: punto dos veces seguidas = punto literal

Con el diseño anterior, `"."` + una letra con símbolo asociado (p.ej. Z →
`:`) siempre resolvía a ese símbolo — no había forma de escribir
literalmente un punto seguido de esa letra. Pedido del usuario: pulsar
`"."` dos veces seguidas debe confirmar el primer punto como literal
(la coma redundante que antes salía de `"."+"."`, vía `SYMBOL_TABLE`, ya
no hace falta — sale directamente y sin ambigüedad con `SHIFT+"."`), y la
tecla que venga después se lee como una pulsación nueva sin combinar.
Así, para escribir ".Z" se teclea "." "." "Z".

Implementado en `input.bas`: si la segunda tecla leída tras un "." es
también un ".", se añade el punto, se descarta la segunda pulsación (no
imprime nada por sí misma, `LastK=0`) y el bucle vuelve a leer una tecla
fresca. Verificado con la misma simulación de programa completo:
`"."+"."` → `a$="."`; `"."+"."+"z"` → `a$=".z"` (sin formar el símbolo
`:`).

## scroll.bas — RESUELTO 2026-07-04 (librería nueva, ejemplo sin cambios)

| Fuente | Prefijo SD81 | Qué prueba | Resultado |
|---|---|---|---|
| `examples/scroll.bas` | SCROLL | Los 4 scrolls pixel-a-pixel (Right/Down/Left/Up) sobre una ventana de 60×60 px, 30 vueltas | Simulado 1200M ticks sin HALT/RST38; pendiente de ver en el emulador (el ejemplo hace 1920 scrolls de hasta 100×100 px, tarda un rato) |

`src/lib/arch/zx48k/stdlib/scroll.bas` no tenía override en zx81sd — se
usaba la versión de zx48k tal cual, y las 8 subs (`ScrollRight/Left/Up/
Down` + sus variantes `*Aligned`) llaman todas a `call 22ACh`, la rutina
*PIXEL-ADD* de la ROM del Spectrum. En zx81sd no hay ROM mapeada: esa
dirección cae en pleno código compilado del programa, y el HALT
reportado (`RST 38` en la traza) era justo el байте que hubiera ahí por
casualidad.

Fix: `src/lib/arch/zx81sd/stdlib/scroll.bas`, copia idéntica salvo las 8
llamadas a `$22AC` sustituidas por `call PIXEL_ADDR` (nuestra propia
rutina, `runtime/pixel_addr.asm`, ya usada por `plot.asm`/`draw.asm` —
ver [[zx81sd-pixel-addr-contract]]). El contrato de registros es
IDÉNTICO al de la ROM (A=191, B=Y, C=X → HL=offset, A=X AND 7, destruye
B, preserva D/E), así que no hizo falta tocar ni una línea del cuerpo de
los bucles de scroll, solo el punto de llamada. `SP.PixelDown`/
`SP.PixelUp` (de zx48k/runtime/SP/) no necesitaron copia: son aritmética
pura sobre `SCREEN_ADDR`, sin ROM, y ya funcionaban igual en zx81sd (se
resuelven por el mecanismo normal de fallback a zx48k cuando no hay
override).

`examples/scroll.bas` no necesitó ningún cambio de fuente — como
`4inarow.bas`, el problema era enteramente de la librería, no del
programa. Añadido a `CAMBIOS_BASIC.md` con esa misma nota.

## maskedsprites.bas — RESUELTO 2026-07-04 (cambio de fuente, no de librería)

| Fuente | Prefijo SD81 | Qué prueba | Resultado |
|---|---|---|---|
| `examples/maskedsprites.bas` → `examples/sd81/maskedsprites_sd81.bas` | MASKED | Sprites enmascarados (AND+OR) con MSFS, 10 sprites animados | Simulado 1000M ticks sin HALT/RST38/escritura ilegal; PC avanza por un rango amplio de direcciones (no atascado) |

A diferencia de `scroll.bas`, aquí el problema SÍ estaba en el propio
ejemplo (`WaitForNewFrame`, definida directamente en `examples/
maskedsprites.bas`, no en la librería `cb/maskedsprites.bas`): hace
`EI` + `HALT` esperando la interrupción IM1 de 50Hz de la ROM del
Spectrum, comparando contra el contador `FRAMES` de la ROM en la
dirección absoluta `23672`. En zx81sd las interrupciones están
permanentemente deshabilitadas (todo el runtime corre con `DI`; el
vector `$0038` es solo una trampa `DI;HALT`, no un manejador real) — ese
`HALT` no despierta nunca. Confirmado con la traza: el simulador se
quedaba con `m.halted=True` exactamente en el `HALT` de `WaitForNewFrame`
tras ~31M ticks.

Fix en `examples/sd81/maskedsprites_sd81.bas`: `WaitForNewFrame` reescrita
para usar `VSYNC_TICK` (`runtime/vsync.asm`, ya usada por `PAUSE`) en vez
de `EI+HALT` — sondea por puerto ($AFh) el contador de pulsos VSYNC
hardware del SD81 Booster, sin depender de interrupciones. El algoritmo
original hacía UN `HALT` inicial y luego un bucle que comprobaba
`FRAMES` SIN esperar de nuevo (confiaba en que la interrupción lo
siguiera incrementando en segundo plano); como en zx81sd nada lo
incrementa solo, el bucle llama a `VSYNC_TICK` explícitamente en cada
vuelta que le falte. `GetInterruptStatusInBorder` se dejó intacta (no se
llama nunca en el bucle principal, solo aparece comentada — se mantiene
únicamente para que la comprobación de compilación del final del fichero
no falle por "función no usada").

### Actualización 2026-07-04: MSFS portado de verdad al mapeador (bloque 7)

El riesgo de `$5B5C`/`$7FFD` de arriba **ya no aplica**: a petición del
usuario ("¿por qué no usamos el bloque 7 que tenemos para bancos?") se
creó `src/lib/arch/zx81sd/stdlib/cb/maskedsprites.bas`, override
completo de la librería compartida (que sigue intacta, regla de
Boriel). Diseño (ver también `CAMBIOS_BASIC.md`):

- **Hallazgo clave**: las funciones de MSFS (`RegisterSpriteImageInMSFS`,
  `FindFirstUnusedBlockInMSFS`, etc.) son agnósticas de banco/dirección
  — solo llaman a `GetBankPreservingRegs`/`SetBankPreservingINTs` y
  leen/escriben la variable BASIC `MaskedSpritesFileSystemStart`.
  Reescribiendo esas dos primitivas (usando el puerto `$E7` sobre el
  **bloque 7**, `$E000-$FFFF` — reservado en nuestro mapa de memoria
  justo para "banking de datos, mapas, sprites") y el cálculo de esa
  dirección en `InitMaskedSpritesFileSystem()` (fija en `$E000` en vez
  de "lo que quede hasta `$FFFF`", que asumía RAM plana Spectrum), el
  resto del fichero (cientos de líneas de álgebra de bloques/bitmap) se
  copió literalmente sin tocar una línea.
- `CheckMemoryPaging()` devuelve `0` (honesto: zx81sd no tiene doble
  pantalla visible al estilo banco 5/7 del Spectrum) sin afectar a
  MSFS, porque las funciones de MSFS no consultan esa función para
  decidir si usar el banco — lo hacen incondicionalmente.
- `SetVisibleScreen`/`GetVisibleScreen`/`ToggleVisibleScreen`/
  `CopyScreen5ToScreen7`/`CopyScreen7ToScreen5`/`SetDrawingScreen5`/
  `SetDrawingScreen7`/`ToggleDrawingScreen` → stubs seguros (doble
  buffer de pantalla real no está cubierto; código muerto en este
  ejemplo dado que `memoryPaging=0`, pero ya no tocan `$5B5C`/`$7FFD`
  por si alguien los llama directamente en el futuro).

**Bug real encontrado durante la implementación** (no por el usuario,
cazado con el propio arnés de simulación): mi primer intento escribió
`SetBankPreservingINTs`/`GetBankPreservingRegs` en BASIC plano en vez de
ASM a mano. Rompía el contrato de registros documentado en el propio
fichero original ("Preserves: D, E, H, L") que el código ASM de
`RegisterSpriteImageInMSFS` y compañía da por hecho (por ejemplo, para
no perder `spriteImageAddr`, que llega en HL) — una función BASIC
compilada usa registros libremente por dentro sin ninguna garantía de
preservarlos. Resultado: los 6 sprites de prueba se registraban todos en
la MISMA dirección (`$0C07`) en vez de direcciones distintas. Se
reescribieron ambas primitivas en ASM a mano, con el mismo contrato
exacto que el original (solo tocan A, B, C).

Verificado con simulación: las 6 direcciones de registro (`regHero0`,
`regFoe00`, `regFoe20-23`) salen correlativas cada 96 bytes exactos
(`$E010, $E070, $E0D0, $E130, $E190, $E1F0`, coincidiendo con
`$E000+n*96+16`), sin disparar `STOP`, y el bucle principal
(`WaitForNewFrame`) se alcanza repetidamente sin cuelgue tras 1000
millones de ticks de simulación sin `HALT`/escritura ilegal.

Limitación conocida del simulador Python usado en esta sesión: no
modela el mapeador de memoria (los `OUT` a `$E7` son no-op en la
simulación, toda la RAM se trata como plana) — no puede validar que el
intercambio de página *físico* funcione de verdad, solo que la lógica
Z80 es correcta asumiendo que sí. La validación definitiva es en el
emulador/hardware real.

### Segunda vuelta 2026-07-04: seguía yéndose a HALT en hardware real

Con el fix de arriba ya compilado, en el emulador real seguía disparando
`__STOP` (mismo síntoma: `RegisterSpriteImageInMSFS` devuelve 0). Traza
confirmó que el problema estaba en `SetBankPreservingINTs`, que hacía el
`OUT` al puerto `$E7` a mano en vez de llamar a `Map()` (mcu.bas):
escribía `A=7` (bloque, sin combinar con la página) con `B=página`. Mi
hipótesis inicial fue que el hardware podía estar en modo simple (donde
el byte de datos debe llevar página Y bloque combinados,
`(página AND 31)<<3 | bloque`, y con solo `A=7` se interpretaría como
página=0) — **el usuario corrigió esto**: el cargador SD81 deja el
mapeador en modo completo desde la línea `LOAD *MAP 7,63`, hasta el
siguiente reset, así que esa explicación concreta no cuadra (en modo
completo solo importan los 3 bits bajos de A, iguales en ambas
versiones). La causa exacta seguía sin confirmarse en el momento de
escribir esto.

Se cambió `SetBankPreservingINTs` para llamar a `Map()` (código ya
probado en otros contextos) en vez de repetir la lógica del puerto a
mano, preservando D,E,H,L alrededor de la llamada con `push`/`pop`
manuales (`Map()` en sí no preserva nada). Tuvo un efecto secundario:
`Map()` dejó de estar referenciada desde BASIC en ningún sitio (solo
desde ASM a mano), y el eliminador de código muerto del compilador la
quitó del binario → `Undefined GLOBAL label '._Map'`. Se resolvió con
una llamada BASIC explícita y redundante a `Map(7, MaskedSprites_MSFS_Page)`
dentro de `InitMaskedSpritesFileSystem()` (comentada como tal — el
análisis de uso del compilador no cuenta las llamadas hechas desde ASM).

Verificado de nuevo en simulación (mismas 6 direcciones correlativas,
sin `STOP`) — pero siguió fallando en el emulador real. El cambio a
`Map()` era, como señaló el usuario, un no-op ("el Map de la biblioteca
hace exactamente lo mismo que el out").

### Causa raíz REAL (tercera vuelta, 2026-07-04): el FSB nunca se inicializa

La traza del usuario mostraba `FindFirstUnusedBlockInMSFS` recorriendo
el free-space bitmap COMPLETO (bucle FIND-INT, 254 líneas de RRCA/DEC E)
y saliendo por la rama `full` (`SCF/RET` → `JR C` → `LD HL,0`): **todos
los bloques aparecían como "ocupados"**. `__EQ16` (el sospechoso
inicial) funcionaba perfectamente — `regHero0` realmente era 0.

Causa: **ni nuestra versión ni la original de zx48k limpian jamás el
FSB** (los bytes del bitmap en `start+2..start+1+l`). En el Spectrum no
hace falta: el test de RAM de la ROM deja toda la memoria a cero en el
arranque, así que el bitmap nace "todo libre" gratis. En zx81sd la
página del bloque 7 llega con basura de fábrica → todos los bits a 1 →
"sin bloques libres" → `RegisterSpriteImageInMSFS` devuelve 0 → `STOP`.

**Por qué el simulador Python dio falso OK dos veces**: su RAM también
nace a ceros, igual que la del Spectrum tras el test de ROM —
exactamente la condición que oculta el bug. Lección de metodología
incorporada al arnés: para validar código que lee memoria no
inicializada, rellenar toda la RAM no cargada con basura (`$FF`) antes
de simular. Con RAM sucia, el binario sin fix reproduce el `STOP` (el
modo de fallo de la traza) y el binario con fix pasa completo (6
registros correctos, bucle principal alcanzado).

Fix (3 líneas + comentario en `InitMaskedSpritesFileSystem`): bucle
`FOR j = start+2 TO start+1+l: poke j,0: NEXT` tras calcular el tamaño
del FSB.

También se verificó por el camino, con `examples/sd81/block7test.bas`
(prefijo BLOCK7), que el mapeador funciona perfectamente: patrones
distintos escritos en páginas 20 y 63 del bloque 7 sobreviven al
intercambio de página (contenido independiente por página). El
mapeador nunca fue el problema.

### Cuarta vuelta 2026-07-04: sprites como líneas verticales — página residente

Con el fix del FSB, en el emulador real MSFS ya inicializaba bien
(pantalla: `Init MSFS at 57344`, `Free Blocks = 85`, y los 6 registros
con los valores EXACTOS que predijo la simulación) pero los sprites se
dibujaban como líneas verticales en vez de sus gráficos.

Causa (descuido de diseño de este override, no del original):
`SaveBackgroundAndDrawSpriteRegisteredInMSFS` — el que dibuja en el
bucle principal y el que fabrica las imágenes desplazadas bajo demanda —
accede a la MSFS **sin envolver con Get/SetBank**. En el diseño original
no lo necesita: en 128K el banco 7 se queda mapeado en `$c000`
(`SetDrawingScreen7`) y en 48K la MSFS está en RAM plana siempre
visible. Nuestra primera versión "liberaba" el bloque 7 de vuelta a la
página 63 al restaurar tras `Init`/`Register...` → el dibujo leía
máscaras y gráficos de la página 63 (basura) → líneas verticales. El
simulador no podía detectarlo: sin mapeador modelado, página 20 y 63
son la misma RAM plana.

Fix: la página de MSFS queda **residente** en el bloque 7 desde el
init — `SetBankPreservingINTs` con valor ≠ 7 solo anota el número, no
desmapea (el "liberar a página 63" era invención de este override,
nada lo necesita). Documentado en la cabecera de la librería: si un
programa usa el bloque 7 para su propio banking, debe remapear su
página él mismo y llamar a `SetBankPreservingINTs(7)` antes de volver a
usar MSFS.
