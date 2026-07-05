#!/usr/bin/env python3
"""
zx81_p_loader.py — Generador de ficheros .p (BASIC tokenizado) para ZX81

Puerto directo a Python del algoritmo de tokenización usado por el emulador
EightyOne (zx81BasicLoader.cpp / IBasicLoader.cpp), referencia:
  C:\\ClaudeCode\\Eightyone2\\src\\zx81\\zx81BasicLoader.cpp
  C:\\ClaudeCode\\Eightyone2\\src\\BasicLoader\\IBasicLoader.cpp

Los comandos extendidos del firmware SD81 Booster (LOAD THEN CLEAR, LOAD *MAP,
LOAD FAST ... CODE, etc.) no necesitan tratamiento especial: aunque esa
sintaxis no la admite el intérprete de la ROM del ZX81, están compuestos por:
  - Tokens estándar del ZX81 (THEN, CLEAR, FAST, CODE, LOAD...) en posiciones
    que la ROM no usaría pero que SÍ se pueden teclear (p.ej. SHIFT+3 = THEN).
  - Palabras sueltas tras un asterisco (p.ej. *MAP, *VER) que son letras
    corrientes, no tokens.
Por tanto basta con tokenizar el texto igual que cualquier BASIC estándar:
el propio algoritmo genérico ya produce la codificación correcta.

No implementa (no hace falta para este proyecto): etiquetas @label, bloques
numéricos [DEC:...]/[HEX:...]/[BIN:...], secuencias de escape \\xx, códigos
gráficos, ni "alternate keyword spelling". Documentados en IBasicLoader.cpp
si en el futuro hicieran falta.
"""

import math
import re
import struct

BLANK = "\x01"          # marcador interno: posición ya consumida
NEWLINE = 0x76
NUMBER_MARK = 0x7E       # precede a los 5 bytes de número embebido
DOUBLE_QUOTE = 0xC0      # comilla escapada ("") dentro de una cadena

# Tokens estándar ZX81 (de zx81BasicLoader::ExtractTokens, sin variantes
# "alternate spelling" ni extensiones ZXpand)
TOKENS = {
    64: "RND",
    65: "INKEY$",
    66: "PI",
    193: "AT ",
    194: "TAB ",
    196: "CODE ",
    197: "VAL ",
    198: "LEN ",
    199: "SIN ",
    200: "COS ",
    201: "TAN ",
    202: "ASN ",
    203: "ACS ",
    204: "ATN ",
    205: "LN ",
    206: "EXP ",
    207: "INT ",
    208: "SQR ",
    209: "SGN ",
    210: "ABS ",
    211: "PEEK ",
    212: "USR ",
    213: "STR$ ",
    214: "CHR$ ",
    215: "NOT ",
    216: "**",
    217: " OR ",
    218: " AND ",
    219: "<=",
    220: ">=",
    221: "<>",
    222: " THEN ",
    223: " TO ",
    224: " STEP ",
    225: " LPRINT ",
    226: " LLIST ",
    227: " STOP ",
    228: " SLOW ",
    229: " FAST ",
    230: " NEW ",
    231: " SCROLL ",
    232: " CONT ",
    233: " DIM ",
    234: " REM ",
    235: " FOR ",
    236: " GOTO ",
    237: " GOSUB ",
    238: " INPUT ",
    239: " LOAD ",
    240: " LIST ",
    241: " LET ",
    242: " PAUSE ",
    243: " NEXT ",
    244: " POKE ",
    245: " PRINT ",
    246: " PLOT ",
    247: " RUN ",
    248: " SAVE ",
    249: " RAND ",
    250: " IF ",
    251: " CLS ",
    252: " UNPLOT ",
    253: " CLEAR ",
    254: " RETURN ",
    255: " COPY ",
}


def ascii_to_zx(c: str) -> int:
    """Puerto de zx81BasicLoader::AsciiToZX."""
    if c.isalpha():
        return (ord(c.upper()) - ord('A')) + 38
    if c.isdigit():
        return (ord(c) - ord('0')) + 28

    table = {
        ' ': 0, '"': 11, '#': 12, '$': 13, ':': 14, '?': 15,
        '(': 16, ')': 17, '-': 22, '+': 21, '*': 23, '/': 24,
        '=': 20, '>': 18, '<': 19, ';': 25, ',': 26, '.': 27,
    }
    if c in table:
        return table[c]

    raise ValueError(f"Caracter invalido: {c!r}")


def zx81_float(value: float) -> bytes:
    """Puerto de zx81BasicLoader::OutputFloatingPointEncoding."""
    exponent = 0
    mantissa = 0

    if value != 0:
        neg = value < 0
        if neg:
            value = -value

        exponent = int(math.floor(1e-12 + (math.log(value) / math.log(2.0))))
        if exponent < -129 or exponent > 126:
            raise OverflowError("Number out of range")

        mantissa_val = (value / (2.0 ** exponent)) - 1
        mantissa_val *= 0x80000000
        mantissa = int(math.floor(mantissa_val))

        exponent += 129

    return bytes([
        exponent & 0xFF,
        (mantissa >> 24) & 0xFF,
        (mantissa >> 16) & 0xFF,
        (mantissa >> 8) & 0xFF,
        mantissa & 0xFF,
    ])


class _Line:
    """Estado de trabajo para una linea BASIC (sin numero de linea), replica
    los buffers mLineBuffer / mLineBufferOutput / mLineBufferPopulated.

    Todos los arrays tienen longitud self.n + 1: el ultimo hueco (indice n)
    es un relleno de seguridad para cuando un token consume el espacio
    artificial añadido al final para detectar tokens sin espacio de cierre
    en el texto original (igual que el buffer sobredimensionado de C++).
    """

    def __init__(self, text: str):
        content = " " + text            # ReadLine antepone siempre un espacio
        self.n = len(content)
        self.buf = list(content) + [BLANK]      # +1 hueco de seguridad
        self.out = [BLANK] * (self.n + 1)
        self.populated = [False] * (self.n + 1)
        # BlankLineStart: sin numero de linea embebido, deja 1 espacio real
        self.buf[0] = ' '


def _mask_copy(chars: list) -> list:
    return list(chars)


def _mask_out_strings(tokenised: list):
    """Puerto de IBasicLoader::MaskOutStrings."""
    text = "".join(tokenised)
    q1 = text.find('"')
    if q1 == -1:
        return
    rem = " REM "
    r1 = text.find(rem)
    if r1 != -1 and r1 < q1:
        return

    within = False
    i = q1
    n = len(tokenised)
    while i < n:
        if tokenised[i] == '"':
            within = not within
        elif within:
            tokenised[i] = BLANK
        else:
            rest = "".join(tokenised[i + 1:])
            nq = rest.find('"')
            if nq == -1:
                return
            nr = rest.find(rem)
            if nr != -1 and nr < nq:
                return
        i += 1


def _mask_out_rem_contents(tokenised: list):
    """Puerto de IBasicLoader::MaskOutRemContents."""
    text = "".join(tokenised)
    rem = " REM "
    pos = 0
    while True:
        r = text.find(rem, pos)
        if r == -1:
            return
        q = text.find('"', pos)
        if q != -1 and q < r:
            q2 = text.find('"', q + 1)
            if q2 == -1:
                return
            pos = q2 + 1
            continue
        start = r + len(rem)
        for i in range(start, len(tokenised)):
            tokenised[i] = BLANK
        return


def _extract_double_quote_characters(line: _Line):
    """Puerto de zx81BasicLoader::ExtractDoubleQuoteCharacters (sin soporte
    de REM tokenizado ni alternate spelling, no necesarios aqui)."""
    buf = line.buf
    n = line.n
    within_quote = False
    i = 0
    while i < n:
        if not within_quote:
            if buf[i] == '"':
                within_quote = True
        else:
            chr1 = buf[i]
            if chr1 == '"':
                if i + 1 < n and buf[i + 1] == '"':
                    buf[i] = BLANK
                    line.out[i] = DOUBLE_QUOTE
                    line.populated[i] = True
                    i += 1
                    buf[i] = BLANK
                else:
                    within_quote = False
        i += 1


def _do_tokenise(line: _Line, tokenised: list):
    """Puerto de IBasicLoader::DoTokenise. Recorre los tokens de codigo mas
    alto a mas bajo (equivalente al reverse_iterator sobre un std::map),
    mutando `tokenised` (busqueda) y line.buf/out/populated (resultado)."""
    for token_code in sorted(TOKENS.keys(), reverse=True):
        token = TOKENS[token_code]
        len_token = len(token)

        start_char = token[0]
        end_char = token[-1]

        token_begins_with_space = start_char == ' '
        token_begins_with_alpha = start_char.isalpha()
        token_ends_with_space = end_char == ' '
        token_ends_with_alpha = end_char.isalpha()

        len_adjustment = 0
        eff_len_token = len_token
        if end_char in ('(', ')', '!', '"', "'", ',', ';', ':') or \
           (end_char == '#' and (len_token < 2 or token[-2] != ' ')) or \
           (end_char == '*' and token != "**"):
            eff_len_token -= 1

        guard = 0
        while True:
            guard += 1
            if guard > 10000:
                raise RuntimeError(f"Bucle de tokenizacion sin fin para {token!r}")

            text = "".join(tokenised)
            pos = text.find(token)
            if pos == -1:
                break

            prev_ok = (token_begins_with_space or not token_begins_with_alpha
                       or (pos == 0) or (not tokenised[pos - 1].isalnum()))
            end_pos = pos + eff_len_token
            next_ok = (token_ends_with_space or not token_ends_with_alpha
                       or (end_pos >= len(tokenised)) or (not tokenised[end_pos].isalnum()))

            if not (prev_ok and next_ok):
                # Coincidencia pegada a un identificador: no es el token,
                # se "rompe" localmente para seguir buscando mas adelante.
                tokenised[pos] = '\x02'
                continue

            start_offset = 1 if token_begins_with_space else 0
            end_offset = (eff_len_token - 1) if token_ends_with_space else (eff_len_token + len_adjustment)

            for b in range(start_offset, end_offset):
                tokenised[pos + b] = BLANK

            for b in range(eff_len_token + len_adjustment):
                idx = pos + b
                if idx < len(line.buf):
                    line.buf[idx] = BLANK

            output_index = pos + start_offset
            if output_index < len(line.out):
                line.out[output_index] = token_code
                line.populated[output_index] = True


def _start_of_number(line: _Line, tokenised: list, index: int) -> bool:
    """Determina si `index` es el inicio de un literal numerico.

    Difiere deliberadamente del original IBasicLoader::StartOfNumber en un
    punto: aqui solo se mira el caracter INMEDIATAMENTE anterior (retrocede
    sobre espacios reales pero se detiene tan pronto encuentra CUALQUIER
    caracter que no sea espacio, sin seguir retrocediendo mas alla). El
    original retrocedia sobre TODOS los espacios consecutivos y comprobaba
    el caracter previo a todos ellos, lo cual en BASIC estandar es
    equivalente (los tokens siempre consumen su propio espacio final como
    BLANK, no como ' ' literal) pero falla en comandos custom del SD81 como
    "*MAP 7,8": "MAP" no es un token reconocido, por lo que el espacio tras
    el queda como ' ' literal, y el algoritmo original terminaba mirando la
    'P' de MAP (alfabetica) y decidia que "7" NO era un numero. En un ZX81
    real, cualquier digito tecleado tras un espacio genera su propio float
    embebido sin importar que palabra le precede, asi que aqui se replica
    ese comportamiento (mas simple y mas correcto para este caso).
    """
    if not (line.buf[index] == '.' or line.buf[index].isdigit()):
        return False

    if index == 0:
        return True

    prev = line.buf[index - 1]
    if prev == ' ':
        return True

    return not (prev.isalpha() or prev.isdigit())


_NUMBER_RE = re.compile(r'[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?')


def _output_embedded_number(line: _Line, index: int, out: bytearray) -> int:
    """Puerto de IBasicLoader::OutputEmbeddedNumber. Devuelve el nuevo
    indice (ya avanzado mas alla del numero, listo para `i += 1` fuera)."""
    n = line.n

    text_no_spaces = ""
    for j in range(index, n):
        if line.buf[j] != BLANK:
            text_no_spaces += line.buf[j]

    m = _NUMBER_RE.match(text_no_spaces)
    if not m or m.end() == 0:
        raise ValueError(f"Numero invalido en posicion {index}: {text_no_spaces!r}")
    number_len_no_spaces = m.end()
    value = float(m.group(0))

    with_spaces_index = 0
    for _ in range(number_len_no_spaces):
        while line.buf[index + with_spaces_index] in (' ', BLANK):
            with_spaces_index += 1
        with_spaces_index += 1

    end_index = index + with_spaces_index

    i = index
    while i < end_index:
        chr_code = line.out[i]
        if chr_code != BLANK and line.populated[i]:
            out.append(chr_code)
        i += 1

    while i < n and line.buf[i] == ' ':
        out.append(ascii_to_zx(' '))
        i += 1

    out.append(NUMBER_MARK)
    out.extend(zx81_float(value))

    return i - 1


def process_line_body(text: str) -> bytes:
    """Tokeniza una linea BASIC (sin numero de linea) y devuelve los bytes
    ya codificados (sin NEWLINE final, que se añade en encode_line)."""
    line = _Line(text)
    n = line.n

    _extract_double_quote_characters(line)

    # Copia de trabajo para deteccion de limites de token: el contenido real
    # (sin el hueco de seguridad de line.buf) + un espacio real extra para
    # detectar tokens sin espacio de cierre en el texto original. Longitud
    # n+1, igual que line.buf, para que los indices sigan alineados.
    tokenised = list(line.buf[:n]) + [' ']

    _mask_out_strings(tokenised)
    _mask_out_rem_contents(tokenised)

    _do_tokenise(line, tokenised)

    # Rellenar cualquier posicion no consumida con su codigo ZX81 directo
    for i in range(1, n):
        if line.buf[i] != BLANK and not line.populated[i]:
            line.out[i] = ascii_to_zx(line.buf[i])
            line.populated[i] = True

    body = bytearray()
    i = 0
    while i < n:
        if line.populated[i]:
            if _start_of_number(line, tokenised, i):
                i = _output_embedded_number(line, i, body) + 1
                continue
            body.append(line.out[i])
        i += 1

    return bytes(body)


def encode_line(line_number: int, text: str) -> bytes:
    body = process_line_body(text) + bytes([NEWLINE])
    return struct.pack('>H', line_number) + struct.pack('<H', len(body)) + body


def encode_program(lines: list) -> bytes:
    """lines: lista de tuplas (numero_de_linea:int, texto:str)."""
    return b"".join(encode_line(n, t) for n, t in lines)


def build_p_file(lines: list) -> bytes:
    """Puerto de zx81BasicLoader::OutputStartOfProgramData +
    ProcessLine(*) + OutputEndOfProgramData. Devuelve el contenido completo
    del fichero .p (desde 0x4009)."""
    data = bytearray()

    def out_byte(b):
        data.append(b & 0xFF)

    def out_word(w):
        data.append(w & 0xFF)
        data.append((w >> 8) & 0xFF)

    def change_word(offset, w):
        data[offset] = w & 0xFF
        data[offset + 1] = (w >> 8) & 0xFF

    # --- OutputStartOfProgramData ---
    out_byte(0x00)          # VERSN
    out_word(0x0000)        # E_PPC
    out_word(0x0000)        # D_FILE
    out_word(0x0000)        # DF_CC
    out_word(0x0000)        # VARS
    out_word(0x0000)        # DEST
    out_word(0x0000)        # E_LINE
    out_word(0x0000)        # CH_ADD
    out_word(0x0000)        # X_PTR
    out_word(0x0000)        # STKBOT
    out_word(0x0000)        # STKEND
    out_byte(0x00)          # BERG
    out_word(0x405D)        # MEM
    out_byte(0x00)          # SPARE1
    out_byte(0x02)          # DF_SZ
    out_word(0x0000)        # S_TOP
    out_word(0xFFFF)        # LAST_K
    out_byte(0x00)          # DBOUNC
    out_byte(0x37)          # MARGIN
    out_word(0x0000)        # NXTLIN
    out_word(0x0000)        # OLDPPC
    out_byte(0x00)          # FLAGX
    out_word(0x0000)        # STRLEN
    out_word(0x0C8D)        # T_ADDR
    out_word(0x4321)        # SEED
    out_word(0xE6E0)        # FRAMES
    out_word(0x0000)        # COORDS
    out_byte(0xBC)          # PR_CC
    out_word(0x1821)        # S_POSN
    out_byte(0x40)          # CDFLAG
    data.extend([0x00] * 32)  # PRBUFF (32 bytes vacios)
    out_byte(0x76)            # PRBUFF (byte 33, NEWLINE)
    data.extend([0x00] * 30)  # MEMBOT
    out_word(0x0000)        # SPARE

    # --- Lineas BASIC ---
    for line_number, text in lines:
        data.extend(encode_line(line_number, text))

    # --- OutputEndOfProgramData ---
    START_OF_RAM = 16393  # 0x4009

    dfile_address = START_OF_RAM + len(data)
    data.extend([NEWLINE] * 25)  # display file colapsado (vacio)

    vars_address = START_OF_RAM + len(data)
    out_byte(0x80)  # fin de VARS (sin variables)

    eline_address = START_OF_RAM + len(data)

    change_word(3, dfile_address)        # D_FILE
    change_word(5, dfile_address + 1)    # DF_CC
    change_word(7, vars_address)         # VARS
    change_word(11, vars_address + 1)    # E_LINE
    change_word(13, vars_address + 5)    # CH_ADD
    change_word(17, eline_address + 5)   # STKBOT
    change_word(19, eline_address + 5)   # STKEND
    change_word(32, vars_address)        # NXTLIN (= VARS => sin autorun)

    return bytes(data)


if __name__ == "__main__":
    import sys

    # Autotest rapido con el loader validado manualmente
    lines = [
        (2, "FAST"),
        (5, "LOAD THEN CLEAR 24575"),
        (10, 'LOAD FAST "BOOT1.BIN"CODE 24576'),
        (20, "LOAD *MAP 7,8"),
        (25, 'LOAD FAST "TESTSD81P8.BIN"CODE 57344'),
        (30, "LOAD *MAP 7,9"),
        (35, 'LOAD FAST "TESTSD81P9.BIN"CODE 57344'),
        (50, "LOAD *MAP 7,63"),
        (60, "RAND USR 24576"),
    ]

    p_data = build_p_file(lines)
    out_path = sys.argv[1] if len(sys.argv) > 1 else "loader_test.p"
    with open(out_path, "wb") as f:
        f.write(p_data)

    print(f"Generado {out_path} ({len(p_data)} bytes)")
    for i in range(0, len(p_data), 16):
        chunk = p_data[i:i + 16]
        hexpart = " ".join(f"{b:02X}" for b in chunk)
        print(f"{i:04X}: {hexpart}")
