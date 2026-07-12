rem Evolution
rem (C) 2026 by Ollibony

#include <play.bas>

cls

let t$ = "T160 W0 X4000 "

let w$ = "V15 O3 1e&&Ee&(e&&&)e& 1d&&Dd&(d&&&)d& 1c&&Cc&(c&&&)c& O2 1a&&Aa&(a&&&)a& "
let x$ = "O3 1e&&Ee&(e&&&)e& 1g&&Gg&g&&&d&4d1& 1c&&Cc&(c&&&)c& O2 1a&&Aa&a&&&a&a&a& "
let y$ = "U O4 3GbG1b3G1b3GbG 3BDB1D3B1D4B1BGD 3ECE1C3E1C3EC1EC 3DaD1a6#C1#CE#C "
let z$ = "3GbG1b3G1b3G O5 1b&D& 3bdb1d3b1d1bdDbgd O4 3ECE1C3E1C3E1CgCb 3ae1aCDE5D#C)"

let i$ = "V15 O5 ((1gab&&&ab&&e&&&d&) 1abC&&&bC&&e&&&d& 1ega&5&&&) "
let j$ = "U O4 3E&E1&3E1&3E&E 3G&G1&3G1&4G& 3C&C1&3C1&3C&& 3a&a1&6a4& "
let k$ = "3E&E1&3E1&3E1G&B& 3G&G1&3G1&4&& 3C&C1&3C1&3C&& 3e&1e4&5ee)"

let q$ = "V0 9&&&&& V15 O5 1bCD&&&CD&&b&&&g& 1CDE&&&DE&&C&&&g& 1Cba&5&&& "
let r$ = "U O4 3b&b1&3b1&3b&b 3D&D1&3D1&4D& 3g&g1&3g1&3g&& 3$F&$F1&6$F4& "
let s$ = "3b&b1&3b1&3b1E&G& 3D&D1&3D1&4&& 3g&g1&3g1&3g&& 3c&1c4&5dd)"

let a$ = t$ + w$ + x$ + y$ + z$
let b$ = i$ + j$ + k$
let c$ = q$ + r$ + s$

print ink 1; a$
print ink 2; b$
print ink 3; c$

Play a$, b$, c$
