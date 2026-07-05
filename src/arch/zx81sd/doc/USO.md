# Uso: compilar, empaquetar y cargar un programa en zx81sd

## 1. Compilar

Desde la raíz de este repositorio:

```
python -m src.zxbc.zxbc <fuente.bas> --arch zx81sd -o <salida.bin> -M <salida.map>
```

- `--arch zx81sd` selecciona el backend y los overrides de esta
  arquitectura (ver [../README.md](../README.md) — regla de oro del port).
- `-M <salida.map>` es opcional pero muy recomendable: genera el mapa de
  símbolos (dirección de cada label ASM/BASIC), imprescindible para
  depurar con un emulador o simular el binario (ver [MAP.md](MAP.md)
  para ejemplos de arneses de simulación en Python).
- Ejemplos transcritos de Sinclair BASIC clásico (arrays/strings
  1-based) suelen necesitar además `--string-base 1 --array-base 1`
  (ver [CAMBIOS_BASIC.md](CAMBIOS_BASIC.md), ejemplo `comecoquitos.bas`).

También existe `python zxbc.py --arch zx81sd -f bin -o <salida.bin> <fuente.bas>`
(script de entrada tradicional); ambas formas son equivalentes.

## 2. Empaquetar para el ZX81

El binario que produce el compilador es una imagen plana de hasta 48KB
(bloques 0-5 del mapeador SD81). El ZX81 solo puede cargar de golpe lo
que quepa en su propia RAM visible, así que hay que partir ese binario
en páginas de 8KB y generar un cargador BASIC que las vaya metiendo en
la tarjeta SD81 Booster una a una, remapeando el mapeador de memoria
entre página y página.

Esto lo hace [`../tools/split_sd81.py`](../tools/split_sd81.py):

```
python src/arch/zx81sd/tools/split_sd81.py <salida.bin> [PREFIJO]
```

- `PREFIJO` (opcional) es el nombre base de los ficheros de salida, en
  el charset del ZX81 (letras, dígitos, sin guion bajo). Si se omite,
  se deriva del nombre del `.bin` de entrada.
- Genera:
  - `<PREFIJO>P8.BIN`, `<PREFIJO>P9.BIN`, ... — una por cada 8KB del
    binario (página SD81 8 = bloque 0, 9 = bloque 1, etc.)
  - `<entrada>_loader.txt` — el listado BASIC del cargador en texto
    plano (para leer/depurar).
  - `<PREFIJO>.P` — el mismo cargador, ya tokenizado, listo para
    cargar y ejecutar en el ZX81 (`LOAD ""` desde la SD).

El cargador generado usa `LOAD THEN CLEAR`, `LOAD *MAP` y
`LOAD FAST ... CODE`, extensiones del firmware del SD81 Booster (no
existen en la ROM original del ZX81). Hace lo siguiente, en orden:

1. Reserva memoria (`CLEAR`) y carga `BOOT1.BIN` (el stage 1, fijo para
   todos los programas — fuente en [`../tools/boot1.asm`](../tools/boot1.asm),
   binario ya ensamblado en [`../tools/boot1.bin`](../tools/boot1.bin)).
2. Por cada página del binario: mapea el bloque 7 a esa página física
   (`LOAD *MAP 7,<n>`) y vuelca los datos ahí (`LOAD FAST ... CODE
   57344`, la ventana del bloque 7 en `$E000`).
3. Al terminar, deja el mapeador en modo "página completa" (`LOAD *MAP
   7,63`) — a partir de aquí el mapeador ya no vuelve a modo simple
   hasta el siguiente reset — y salta a `BOOT1.BIN` (`RAND USR 24576`),
   que hace el mapeo definitivo de los bloques 0-5 y arranca el
   programa.

## 3. Copiar a la tarjeta SD

Copia a la SD, junto al resto de tu colección:

- `BOOT1.BIN` (una sola vez, es el mismo para todos los programas)
- Todas las `<PREFIJO>P<n>.BIN` del programa
- `<PREFIJO>.P`

Y en el ZX81 (o en EightyOne apuntando a la imagen de la SD): `LOAD ""`
y selecciona `<PREFIJO>`.

## 4. Depurar sin hardware: simulación con Python

Para diagnosticar cuelgues, HALTs o resultados incorrectos sin tener
que probar en el emulador o el hardware real cada vez, el desarrollo de
este port ha usado el paquete `z80` de Python (`pip install z80`) para
simular el binario plano directamente. La metodología completa
(incluida una trampa importante: la RAM del simulador nace a ceros, lo
que puede ocultar bugs de memoria no inicializada que sí aparecen en
hardware real) está documentada en [MAP.md](MAP.md) — sección "Heap en
$8100 + traps de cinta de EightyOne" y las notas de metodología del bug
de MSFS/maskedsprites.
