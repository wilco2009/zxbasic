#!/usr/bin/env python3
"""
split_sd81.py — Particionador de binario ZX81+SD81 Booster + generador de loader

Divide el binario plano generado por zxbc.py (--arch zx81sd, -f bin)
en páginas de 8KB para su carga desde el cargador BASIC del ZX81, y genera
el listado BASIC (texto plano, no tokenizado) necesario para cargarlas.

Mapa de páginas:
  Página 8  → bloque 0 ($0000-$1FFF): vectors + stage2 + runtime + código usuario
  Página 9  → bloque 1 ($2000-$3FFF): continuación si el binario supera 8KB
  Página 10 → bloque 2 ($4000-$5FFF): ídem
  Página 11 → bloque 3 ($6000-$7FFF): ídem  (stage 1 externo reside aquí antes del salto)
  Página 12 → bloque 4 ($8000-$9FFF): sysvars + heap (datos, no ejecutable sin MC45)
  Página 13 → bloque 5 ($A000-$BFFF): heap continuación

El binario empieza en $0000 y no incluye cabecera .tap/.tzx.
Cada fichero de salida se llama <BASE>P<N>.BIN (mayúsculas) donde N es la página.

El loader BASIC generado (texto plano, aún no tokenizado a .p) sigue la
secuencia validada manualmente sobre hardware/emulador:

  2 FAST
  5 LOAD THEN CLEAR 24575
  10 LOAD FAST "BOOT1.BIN"CODE 24576
  20 LOAD *MAP 7,8
  25 LOAD FAST "<BASE>P8.BIN"CODE 57344
  30 LOAD *MAP 7,9
  35 LOAD FAST "<BASE>P9.BIN"CODE 57344
  ...
  <N0> LOAD *MAP 7,63
  <N0+10> RAND USR 24576

Nota: "LOAD THEN CLEAR", "LOAD *MAP" y "LOAD FAST ... CODE" son extensiones
propias del firmware del SD81 Booster sobre el BASIC del ZX81 (no existen en
la ROM original). El bloque 7 ($E000/57344) se usa como ventana de paginación
temporal para volcar cada página física antes de que BOOT1.BIN haga el mapeo
definitivo de bloques 0-5 vía el puerto $E7. El "LOAD *MAP 7,63" final fuerza
el cambio a modo full-paging (64 páginas) y deja el bloque 7 en un estado
neutro antes de saltar al programa.

Además del listado en texto plano, genera el .p tokenizado real (listo para
cargar/ejecutar) usando zx81_p_loader.py, un puerto a Python del tokenizador
de EightyOne (zx81BasicLoader.cpp / IBasicLoader.cpp).

Uso:
  python split_sd81.py <entrada.bin> [salida_base]

  Si no se especifica salida_base, se usa el nombre de entrada sin extensión.

Ejemplo:
  python split_sd81.py test_sd81.bin
  → TEST_SD81P8.BIN  (primera página, siempre presente)
  → TEST_SD81P9.BIN  (solo si el binario supera 8 KB)
  → ...
  → test_sd81_loader.txt  (listado BASIC del cargador, texto plano)
  → TEST_SD81.P           (mismo listado, tokenizado)
"""

import sys
import os

from zx81_p_loader import build_p_file

PAGE_SIZE = 8192        # 8KB por página
FIRST_PAGE = 8          # página SD81 asignada al bloque 0
CLEANUP_PAGE = 63       # página neutra: fuerza modo full-paging (64 páginas)
BOOT1_FILE = "BOOT1.BIN"
BOOT1_ADDR = 24576      # $6000
CLEAR_ADDR = 24575      # protege BOOT1.BIN (reservado justo debajo)
LOAD_WINDOW_ADDR = 57344  # $E000, ventana de bloque 7


def split(input_path: str, output_base: str) -> list[str]:
    with open(input_path, "rb") as f:
        data = f.read()

    if not data:
        sys.exit(f"Error: {input_path} está vacío")

    pages_written = []
    page_num = FIRST_PAGE
    offset = 0

    while offset < len(data):
        chunk = data[offset : offset + PAGE_SIZE]

        # Rellenar hasta PAGE_SIZE con 0xFF (valor indefinido de FLASH/RAM sin inicializar)
        if len(chunk) < PAGE_SIZE:
            chunk = chunk + b"\xff" * (PAGE_SIZE - len(chunk))

        out_path = f"{output_base}P{page_num}.BIN"
        with open(out_path, "wb") as f:
            f.write(chunk)

        pages_written.append(out_path)
        print(
            f"  Pagina {page_num} (bloque {page_num - FIRST_PAGE}): "
            f"{out_path}  "
            f"[{offset:#06x} - {min(offset + PAGE_SIZE - 1, len(data) - 1):#06x}]"
        )

        offset += PAGE_SIZE
        page_num += 1

    return pages_written


def generate_loader_lines(page_files: list[str]) -> list[tuple[int, str]]:
    lines = []
    lines.append((2, "FAST"))
    lines.append((5, f"LOAD THEN CLEAR {CLEAR_ADDR}"))
    lines.append((10, f'LOAD FAST "{BOOT1_FILE}"CODE {BOOT1_ADDR}'))

    line_no = 20
    for i, page_file in enumerate(page_files):
        page_num = FIRST_PAGE + i
        lines.append((line_no, f"LOAD *MAP 7,{page_num}"))
        lines.append((line_no + 5, f'LOAD FAST "{page_file}"CODE {LOAD_WINDOW_ADDR}'))
        line_no += 10

    lines.append((line_no, f"LOAD *MAP 7,{CLEANUP_PAGE}"))
    lines.append((line_no + 10, f"RAND USR {BOOT1_ADDR}"))

    return lines


def generate_loader_text(lines: list[tuple[int, str]]) -> str:
    return "\n".join(f"{n} {cmd}" for n, cmd in lines) + "\n"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_base = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(input_path)[0]
    output_base = os.path.basename(output_base).upper()

    # Los nombres de fichero de las paginas y del loader.p se escriben en el
    # charset del ZX81 (letras, digitos y unos pocos simbolos: sin guion
    # bajo ni otros caracteres no representables). Fallar pronto y claro en
    # vez de que reviente mas tarde al tokenizar el loader.
    from zx81_p_loader import ascii_to_zx
    for c in output_base:
        try:
            ascii_to_zx(c)
        except ValueError:
            sys.exit(
                f"Error: el nombre base {output_base!r} contiene {c!r}, "
                "no representable en el charset ZX81 (evita '_' y similares)."
            )

    if not os.path.isfile(input_path):
        sys.exit(f"Error: no se encuentra {input_path!r}")

    size = os.path.getsize(input_path)
    num_pages = (size + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"Binario: {input_path}  ({size} bytes, {size/1024:.1f} KB, {num_pages} pagina/s)")
    print(f"Particionando en paginas de {PAGE_SIZE} bytes (pagina SD81 inicial = {FIRST_PAGE})...")
    print()

    pages = split(input_path, output_base)

    print()
    print(f"Generados {len(pages)} fichero/s.")
    if len(pages) == 1:
        print("El programa cabe en una sola pagina (8 KB).")
    else:
        print(f"Paginas {FIRST_PAGE} a {FIRST_PAGE + len(pages) - 1}.")

    loader_lines = generate_loader_lines(pages)
    loader_text = generate_loader_text(loader_lines)

    # El .p es un nombre de fichero real para el ZX81 (charset sin guion
    # bajo): se deriva de output_base (mismo prefijo que las paginas),
    # concatenado sin separador, igual que "<BASE>P8.BIN".
    base_no_ext = os.path.splitext(input_path)[0]
    loader_txt_path = f"{base_no_ext}_loader.txt"
    loader_p_path = f"{output_base}.P"

    with open(loader_txt_path, "w", newline="\n") as f:
        f.write(loader_text)

    p_data = build_p_file(loader_lines)
    with open(loader_p_path, "wb") as f:
        f.write(p_data)

    print()
    print(f"Loader BASIC (texto plano): {loader_txt_path}")
    print("---")
    print(loader_text, end="")
    print("---")
    print(f"Loader BASIC tokenizado (.p): {loader_p_path}  ({len(p_data)} bytes)")
    print()
    print("NOTA: 'LOAD THEN CLEAR', 'LOAD *MAP' y 'LOAD FAST ... CODE' son extensiones")
    print("del firmware SD81 Booster, codificadas con el mismo mecanismo de tokens que")
    print("el BASIC estandar del ZX81 (ver zx81_p_loader.py).")
    print(f"Copia {BOOT1_FILE}, los ficheros de pagina y {os.path.basename(loader_p_path)}")
    print("a la tarjeta SD.")


if __name__ == "__main__":
    main()
