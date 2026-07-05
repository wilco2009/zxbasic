; ===========================================================================
; bootstrap_stage1.asm — Stage 1 Bootstrap ZX81 + SD81 Booster
;
; Reside en $6000 (bloque 3).  El cargador BASIC lo envía allí antes de
; nada porque es una zona neutral: BASIC del ZX81 no la necesita, y aún
; no hemos remapeado ningún bloque.
;
; Secuencia de inicio (ver ZX81-SD81-Adaptation-Plan.md):
;   1. DI  — deshabilitar interrupciones (el ZX81 FAST mode ya lo hace, pero
;             lo repetimos por seguridad antes de tocar la paginación)
;   2. Activar modo Superfast HiRes Spectrum vía FPGA (POKE 2045 = $07FD)
;   3. Desactivar IO mapeado en memoria     (POKE 2056 = $0808)
;   4. Mapear bloque 0 → página 8 (OUT ($E7), page=8, block=0)
;      El stage 2 ($0100-$0FFF en página 8) está ahora listo para ejecutar.
;   5. JP $0100  — salta al stage 2 en la RAM recién mapeada
;
; Notas:
;   - HFILE=$C000 es el valor por defecto de la FPGA al activar modo 172.
;     Si tu hardware requiere configurarlo explícitamente, descomenta el
;     bloque HFILE al final.
;   - El stage 1 NO inicializa SP; el stage 2 lo hace (ld sp, $7FFF).
;   - Bloques 1-5 se mapean en el stage 2 (ya ejecutando desde página 8).
;
; Compilar:
;   zxbasm bootstrap_stage1.asm -o bootstrap_stage1.bin
; o con pasmo:
;   pasmo --bin bootstrap_stage1.asm bootstrap_stage1.bin
;
; Cargar en el emulador / hardware a dirección $6000 (24576 decimal).
; Ejecutar desde BASIC con:
;   RANDOMIZE USR 24576
; ===========================================================================

    org $6000

SD81_STAGE1:

    di                          ; Interrupciones desactivadas

	; --------------------------------------------------------------------------
	; Asignar la direccion del framebuffer (HFILE)
	; high=2044 low=(2043)
	;
	
	ld   hl, $C000
	ld   ($07FB), hl 
	
	; --------------------------------------------------------------------------
    ; ------------------------------------------------------------------
    ; Activar modo Superfast HiRes Spectrum
    ; POKE 2045, 172  →  ld a, 172 / ld ($07FD), a
    ; La FPGA del SD81 Booster interpreta esto como:
    ;   modo 172 ($AC) = Spectrum 256x192 desde HFILE=$C000
    ; ------------------------------------------------------------------
    ld   a, 172
    ld   ($07FD), a

    ; ------------------------------------------------------------------
    ; Desactivar IO mapeado en memoria
    ; POKE 2056, 0  →  ld ($0808), a
    ; Evita colisiones entre las instrucciones IN/OUT y el espacio de RAM
    ; ------------------------------------------------------------------
    xor  a
    ld   ($0808), a

    ; ------------------------------------------------------------------
    ; Mapear bloque 0 ($0000-$1FFF) → página 8 del SD81
    ; Puerto $E7: modo full 64 páginas, OUT (C), A con B=página, A=bloque
    ; La página 8 contiene el binario compilado (vectors + stage 2 + runtime)
    ; ------------------------------------------------------------------
    ld   b, 8                   ; página SD81 destino (8 = primera página de usuario)
    ld   a, 0                   ; bloque Z80 a reasignar (bloque 0 = $0000-$1FFF)
    ld   c, $E7                 ; puerto de paginación SD81
    out  (c), a                 ; mapear  (B=página, A=bloque)

    ; ------------------------------------------------------------------
    ; Saltar al stage 2 en la RAM recién mapeada
    ; A partir de aquí el bloque 0 contiene la página 8:
    ;   $0000-$0067  vectores RST
    ;   $0100        __START_PROGRAM (inicio del stage 2)
    ; ------------------------------------------------------------------
    jp   $0100


    end SD81_STAGE1
