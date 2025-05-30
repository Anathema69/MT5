import MetaTrader5 as mt5
import sys

# 1) Inicializa MT5
if not mt5.initialize():
    print("Error al inicializar MT5:", mt5.last_error())
    mt5.shutdown()
    sys.exit()

# 2) Obtén todos los símbolos
all_syms = mt5.symbols_get()

# 3) Filtra solo los que pertenecen al grupo “Forex” puro
forex = sorted({
    sym.name
    for sym in all_syms
    # partimos el path por “\” y comprobamos que la primera sección sea exactamente “Forex”
    if sym.path.split("\\", 1)[0].lower() == "forex"
})

# 4) Imprime el resultado
print("Pares Forex puros disponibles:")
for s in forex:
    print(s)

# 5) Cierra la conexión
mt5.shutdown()
