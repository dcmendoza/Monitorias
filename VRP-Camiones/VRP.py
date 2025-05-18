import pandas as pd
import math

# Parámetros
CAPACIDAD_MAX = 15        # kg
VEL_MED = 60              # km/h
T_DESPACHO = 10           # min
T_RECARGA  = 20           # min
T_JORNADA  = 7 * 60       # min

# 1. Leer clientes
df = pd.read_excel('/mnt/data/clientes.xlsx', engine='openpyxl')
df['asignado'] = False  # marcar asignación

# 2. Función distancia euclidiana
def distancia(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

# 3. Inicializar 4 camiones
camiones = [
    {'ruta': [(0, 0)], 'carga': 0, 'tiempo': 0, 'ultima': (0, 0)}
    for _ in range(4)
]

print("Clientes cargados:", len(df))
