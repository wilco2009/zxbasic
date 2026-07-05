# Cambios en fuentes BASIC para portar ejemplos oficiales a zx81sd

Este fichero recopila, para cada ejemplo oficial de `examples/` que se ha
probado en zx81sd, si hizo falta tocar el fuente BASIC (nunca el original:
siempre una copia en `examples/sd81/`) o solo cambiar las flags de
compilación.

Regla de fondo: el fuente oficial de zxbasic **nunca se modifica**. Cuando
un programa depende de una sysvar o dirección absoluta específica del
Spectrum, se hace una copia adaptada junto al original.

---

## 1. `examples/english/comecoquitos.bas` — SIN cambios de fuente

Compila tal cual. Solo necesita flags de línea de comandos:

```
python -m src.zxbc.zxbc comecoquitos.bas --arch zx81sd --string-base 1 --array-base 1 -o comecocos.bin
```

**Por qué**: el fuente usa indexación de strings 1-based (estilo Sinclair
BASIC clásico, `l$(f)`, slicing). Con la base 0 por defecto de zxbasic,
las comparaciones de colisión salen desplazadas una posición — no es un
bug del port, en zx48k pasa exactamente igual sin esas flags.

---

## 2. `examples/english/snake_en.bas` → `examples/sd81/snake_sd81.bas`

Un solo cambio, una línea:

```diff
-73   POKE UINTEGER 23675, @udg(0, 0): REM Sets UDG variable to first element
+73	 POKE UINTEGER $8002, @udg(0, 0): REM sysvar UDG de zx81sd (en Spectrum era 23675)
```

**Por qué**: `23675` ($5C7B) es la dirección absoluta del sysvar `UDG` en
el mapa de memoria del **Spectrum**. En zx81sd el mismo sysvar vive en
`$8002` (ver `SYSVAR_BASE+2` en `src/lib/arch/zx81sd/runtime/sysvars.asm`).
Sin el cambio, el POKE cae en RAM libre y los UDGs (cabeza y fruta de la
serpiente) nunca se activarían — el juego funcionaría pero pintaría
espacios en vez de los gráficos.

**Patrón general**: cualquier ejemplo que haga `POKE`/`PEEK` a una
dirección de sysvar del Spectrum en vez de usar la función de más alto
nivel (aquí habría bastado con no usar UDG a pelo) necesita este tipo de
traducción de dirección. Ver también flights.bas más abajo.

---

## 3. `examples/flights.bas` → `examples/sd81/flights_sd81.bas`

Tres cambios de contenido (más limpieza cosmética de espacios finales sin
efecto funcional, no listada):

### 3.1 Eliminar un POKE de sysvar del Spectrum sin equivalente

```diff
-1 POKE 23658,8: BORDER 1: PAPER 1: INK 7: CLS 
+1 BORDER 1: PAPER 1: INK 7: CLS
```

**Por qué**: `23658` ($5C6A) es `REPDEL` (retardo de repetición de tecla)
en el Spectrum — no existe ese sysvar en zx81sd, y el POKE escribiría
sobre una dirección de RAM arbitraria. Se elimina sin más: el efecto
(ajustar el auto-repeat del teclado) no tiene equivalente ni falta le
hace al juego.

### 3.2 Traducir el sysvar COORDS a su dirección real en zx81sd

```diff
-2295 IF gc<>0 THEN PLOT OVER 1;x1,168+16-y1: DRAW OVER 1;x2-PEEK 23677,168+16-y2-PEEK 23678: END IF
+2295 IF gc<>0 THEN PLOT OVER 1;x1,168+16-y1: DRAW OVER 1;x2-PEEK $8004,168+16-y2-PEEK $8005: END IF
```
(y tres apariciones más idénticas en las líneas 2370, 2378 y 2445)

**Por qué**: `23677`/`23678` ($5C7D/$5C7E) son el sysvar `COORDS`
(última coordenada de `PLOT`) del Spectrum. En zx81sd vive en `$8004`/
`$8005` (`COORDS EQU SYSVAR_BASE+$04` en `sysvars.asm`). Sin la
traducción, los `PEEK` leen RAM del programa compilado en vez de la
coordenada real, y el `DRAW` de la línea del horizonte sale con un
desplazamiento aleatorio dependiente del contenido de esa RAM — este fue
el primer síntoma reportado ("pinta mal la línea del horizonte").

### 3.3 Comparaciones de tecla a minúsculas

```diff
-3010 IF k$="S" THEN LET pow=pow-1: END IF
-3020 IF k$="F" THEN LET pow=pow+1: END IF
-3030 IF k$="Q" THEN LET pt=pt+1: END IF
-3040 IF k$="A" THEN LET pt=pt-1: END IF
-3050 IF k$="O" AND rl>-30 THEN LET rl=rl-1: END IF
-3060 IF k$="P" AND rl<30 THEN LET rl=rl+1: END IF
+3010 IF k$="s" THEN LET pow=pow-1: END IF
+3020 IF k$="f" THEN LET pow=pow+1: END IF
+3030 IF k$="q" THEN LET pt=pt+1: END IF
+3040 IF k$="a" THEN LET pt=pt-1: END IF
+3050 IF k$="o" AND rl>-30 THEN LET rl=rl-1: END IF
+3060 IF k$="p" AND rl<30 THEN LET rl=rl+1: END IF
```
(y las comparaciones de "Y"/"N" en las líneas 6150/6160)

**Por qué (este cambio corresponde al esquema de teclado antiguo — ver
nota de "ya no es necesario" más abajo)**: en el momento de portar
`flights.bas`, `zx81sd/runtime/io/keyboard/keyscan.asm` (reescaneo a
mano del **teclado físico del ZX81**, 40 teclas, ya que el SD81 Booster
no tiene teclado Spectrum) solo devolvía minúscula siempre, sin importar
si se pulsaba `SHIFT` o no — `SHIFT+letra` no producía la mayúscula de
esa letra, sino uno de los símbolos clásicos del ZX81 (dos puntos,
comillas, `+`, `-`...). Con ese esquema no existía combinación física
que reprodujera "CAPS SHIFT+S" al estilo Spectrum, y la única
adaptación posible era comparar contra minúscula sin shift. Mismo
motivo, ya resuelto antes por otra vía en `comecoquitos.bas` (ahí el
propio fuente ya comparaba en minúscula, "o","p","q","a","y","n" —
coincidencia de que su autor tecleó así, no algo que tuviéramos que
tocar) y en `snake_sd81.bas` (compara "O"/"o" con `OR`, cubriendo ambos
casos sin necesidad de tocarlo).

**Ya no es necesario (2026-07-04)**: `keyscan.asm` se rediseñó para que
la pulsación directa de una letra dé minúscula y `SHIFT+letra` dé la
MAYÚSCULA de esa letra (además de `SHIFT+"2"` como CAPS LOCK persistente
y los símbolos clásicos del ZX81 alcanzables con `"."+tecla` desde
`INPUT()`). Con el esquema actual, `INKEY$="S"` ya funcionaría de forma
natural pulsando `SHIFT+S`, exactamente como en un Spectrum — el cambio
de caso de `flights_sd81.bas` documentado arriba fue necesario en su
momento pero ya no lo sería si se portara hoy desde cero. Se deja
constancia aquí en vez de revertir la copia ya probada. Detalle completo
del rediseño en [MAP.md](MAP.md), sección "Esquema de teclado nuevo".

---

## 4. `examples/english/4inarow.bas` — SIN cambios de fuente

Compila con flags por defecto:

```
python -m src.zxbc.zxbc 4inarow.bas --arch zx81sd -o row4.bin
```

Sus arrays usan índices 1..8 que caben en base 0 por defecto sin
colisión de slicing (no hace slicing de strings), y sus comparaciones de
tecla ya usan minúsculas ("y"/"n" en los prompts). Ejercita el código de
arcos (`DRAW 8,0,PI`) y `CIRCLE` sin necesitar ningún parche.

---

## 5. `examples/scroll.bas` — SIN cambios de fuente

Compila con flags por defecto:

```
python -m src.zxbc.zxbc scroll.bas --arch zx81sd -o scroll.bin
```

El problema no estaba en el ejemplo sino en la librería: `scroll.bas` no
tenía versión zx81sd — se usaba tal cual la de zx48k, cuyas 8 subs
(`ScrollRight/Left/Up/Down` + variantes `*Aligned`) llaman a `$22AC`
(rutina *PIXEL-ADD* de la ROM del Spectrum, inexistente en zx81sd). Se
creó `src/lib/arch/zx81sd/stdlib/scroll.bas`, idéntica salvo sustituir
esas 8 llamadas por `call PIXEL_ADDR` (nuestra propia implementación,
mismo contrato de registros que la ROM — ver [MAP.md](MAP.md)). El
ejemplo en sí no necesitó ningún cambio, igual que 4inarow.bas.

---

## 6. `examples/maskedsprites.bas` → `examples/sd81/maskedsprites_sd81.bas`

**En proceso — aún no funciona del todo bien.**

Un cambio de fondo: `WaitForNewFrame` (definida en el propio ejemplo, no
en la librería) reescrita para no depender de interrupciones:

```diff
-    ld de,23672
-    ld c,a      ; A = C = minimumNumberofFramesToWaitSinceLastWait
-    READ_IFF2
-    ex af,af'    
-    ei          ; interrupts MUST be enabled before HALT
-    halt
+    ld de, FRAMES
+    ld c,a      ; C = minimumNumberofFramesToWaitSinceLastWait
+    call VSYNC_TICK ; garantiza al menos un frame esperado (sustituye EI+HALT)
 wait:
     ld a,(de)
     sub (hl)
     cp c
-    jr c,wait
-    ld a,(de)
-    ld (hl),a
-    ex af,af'
-    ret pe
-    di
-    RET
+    jr nc,enough
+    call VSYNC_TICK
+    jr wait
+enough:
+    ld a,(de)
+    ld (hl),a
+    ret
```

**Por qué**: `23672` es el contador `FRAMES` de la ROM del Spectrum,
incrementado automáticamente por la interrupción IM1 de 50Hz. El
original hace un `HALT` inicial (espera a la interrupción) y luego un
bucle que confía en que la interrupción lo siga incrementando en segundo
plano mientras el bucle solo *comprueba* sin volver a esperar. En
zx81sd no hay interrupciones (DI permanente; el vector `$0038` es una
trampa `DI;HALT`, no un manejador real) — ese `HALT` no despertaría
nunca. Se sustituye por `VSYNC_TICK` (sondeo del contador de pulsos
VSYNC hardware del SD81 Booster por puerto, la misma rutina que ya usa
`PAUSE`), llamada explícitamente en cada vuelta que haga falta esperar.

**Actualización — MSFS portado al mapeador de zx81sd (bloque 7)**: el
riesgo de arriba ya no aplica. Se creó
`src/lib/arch/zx81sd/stdlib/cb/maskedsprites.bas` (override completo de
la librería compartida, que sigue intacta): `SetBankPreservingINTs`/
`GetBankPreservingRegs` reescritas en ASM a mano sobre el puerto `$E7`
(bloque 7, `$E000-$FFFF` — reservado en nuestro mapa de memoria para
"banking de datos, mapas, sprites"), y `MaskedSpritesFileSystemStart`
fija en `$E000` en vez de "lo que quede hasta `$FFFF`" (que asumía RAM
plana Spectrum). El resto de MSFS (cientos de líneas de álgebra de
bloques) es agnóstico de banco/dirección y se copió sin tocar una línea.
Detalle completo, incluido un bug real cazado en el proceso (registros
no preservados si se escriben en BASIC en vez de ASM), en [MAP.md](MAP.md).

Pese a los fixes de arriba (confirmados con simulación y, en parte, en
emulador/hardware real), la librería en su estado actual **sigue sin
funcionar del todo bien** — trabajo en curso, no dar por cerrado este
ejemplo todavía.

---

## 7. `examples/sd81/pong.bas` — transcripción clásica, un cambio ASM

No es un ejemplo oficial de `examples/` sino una transcripción clásica
de Pong al estilo Sinclair BASIC (GOSUB/números de línea), añadida
directamente en `examples/sd81/`. Usa comparaciones de tecla ya en
minúscula ("4","q","3","a"), coincidentes con el esquema de teclado
actual sin necesidad de tocar nada — el único cambio fue sustituir la
sincronización de pantalla:

```diff
     ASM
-    call VSYNC_TICK ; garantiza al menos un frame esperado (sustituye EI+HALT)
+    call .core.VSYNC_TICK ; garantiza al menos un frame esperado (sustituye EI+HALT)
     ; halt        ; Avoids screen flickering
     END ASM
```

**Por qué**: `vsync.asm` envuelve `VSYNC_TICK` en
`push namespace core ... pop namespace`; al llamarlo desde un bloque
`ASM ... END ASM` que no está dentro de ese namespace hace falta el
prefijo completo `.core.VSYNC_TICK` — mismo patrón de error que en
`maskedsprites_sd81.bas` (ver [PRECAUCIONES.md](PRECAUCIONES.md),
sección 5). Sin el prefijo, el compilador da
`Undefined GLOBAL label '.VSYNC_TICK'`.

---

## 8. `examples/sd81/block7test.bas` — sin equivalente oficial, prueba de mapeador

Programa mínimo (no transcripción de ningún ejemplo) escrito para
confirmar, de forma aislada, que el mapeador de memoria del SD81 Booster
provee almacenamiento independiente por página: escribe patrones
distintos en las páginas 20 y 63 del bloque 7 (`$E000-$FFFF`) vía
`Map()` y verifica que no se pisan entre sí. Sirvió para descartar el
mapeador como causa durante la investigación del bug de MSFS (ver
[MAP.md](MAP.md)). Se conserva como ejemplo de referencia de uso directo
de `Map()`/`MapGet` sobre el bloque 7.

---

## Resumen para el manual

| Ejemplo | Copia en zx81sd | Cambios de fuente | Flags de compilación |
|---|---|---|---|
| comecoquitos.bas | no hace falta copia si no se toca el original | ninguno | `--string-base 1 --array-base 1` |
| snake_en.bas | `snake_sd81.bas` | 1 línea (dirección UDG) | ninguna especial |
| flights.bas | `flights_sd81.bas` | 3 tipos de cambio (POKE eliminado, 4× PEEK COORDS, 8× case de tecla) | ninguna especial |
| 4inarow.bas | no hace falta copia | ninguno | ninguna especial |
| scroll.bas | no hace falta copia | ninguno (el fix fue en la librería `stdlib/scroll.bas`) | ninguna especial |
| maskedsprites.bas | `maskedsprites_sd81.bas` | `WaitForNewFrame` reescrita (EI+HALT → VSYNC_TICK); librería `cb/maskedsprites.bas` portada al mapeador (bloque 7) — **en proceso, aún no funciona del todo bien** | ninguna especial |
| pong.bas (no oficial) | `pong.bas` en `examples/sd81/` | 1 línea ASM (namespace de VSYNC_TICK) | ninguna especial |
| block7test.bas (no oficial) | `block7test.bas` en `examples/sd81/` | n/a (escrito directamente para zx81sd) | ninguna especial |

Patrón identificado para futuros ejemplos:

1. Buscar `POKE`/`PEEK` a literales numéricos: casi siempre es una
   sysvar del Spectrum que hay que traducir a su dirección zx81sd
   equivalente (ver `src/lib/arch/zx81sd/runtime/sysvars.asm`).
2. Comparaciones de `INKEY$` contra mayúsculas de teclas de control
   (`"S"`, `"Q"`, etc.): con el esquema de teclado **actual**
   (pulsación directa = minúscula, `SHIFT+letra` = mayúscula) esto ya
   funciona igual que en un Spectrum y **no hace falta tocar nada** —
   el cambio a minúscula documentado arriba para `flights.bas`
   corresponde a una versión anterior de `keyscan.asm` (ver nota "Ya no
   es necesario" en la sección 3.3) y se mantiene aquí solo como
   registro histórico de esa copia ya generada.
3. Código ASM inline que llame a rutinas envueltas en
   `push namespace core` (como `VSYNC_TICK`) necesita el prefijo
   `.core.` si el bloque `ASM` que lo invoca no está ya dentro de ese
   namespace (ver caso de `pong.bas` arriba).
