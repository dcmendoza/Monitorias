"""
Vehicle Routing Problem (VRP) con recarga intermedia y planificación multi-día.

Este script:
1. Lee un listado de clientes con coordenadas y peso de entrega.
2. Planifica rutas diarias para una flota de 4 camiones:
   - Capacidad máxima por camión.
   - Jornada de 7 horas (420 min).
   - Tiempo de despacho fijo por cliente.
   - Posibilidad de volver al depósito para recargar (vaciar carga).
3. Repite día tras día hasta servir a todos los clientes.
4. Genera un PDF con:
   - Tabla de entregas (día, camión, cliente, llegada, salida, distancia tramo).
   - Tabla de métricas (día, camión, distancia total, tiempo total).
   - Gráfico de rutas en coordenadas X–Y.
"""

import pandas as pd
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# -----------------------------------------------------------------------------
# 1. PARÁMETROS DEL PROBLEMA
# -----------------------------------------------------------------------------
CAPACIDAD_MAX = 15       # kg máximo que puede transportar cada camión
VEL_MED       = 60       # km/h velocidad media de circulación
T_DESPACHO    = 10       # min fijos para descargar en cada cliente
T_RECARGA     = 20       # min para volver al depósito y vaciar el camión
T_JORNADA     = 7 * 60   # min total de jornada diaria (7 h = 420 min)

# -----------------------------------------------------------------------------
# 2. LECTURA Y PREPARACIÓN DE DATOS
# -----------------------------------------------------------------------------
# 2.1. Cargar clientes desde un archivo Excel:
#      Cada fila debe tener: Cliente ID, Coordenada X, Coordenada Y, Peso (kg).
df = pd.read_excel('clientes.xlsx', engine='openpyxl')

# 2.2. Inicializar columnas de estado para cada cliente:
#      - 'asignado': si ya fue atendido (bool)
#      - 'día_entrega': día en que se realizó la entrega (int)
df['asignado']    = False
df['día_entrega'] = None

# -----------------------------------------------------------------------------
# 3. DICCIONARIO DE COORDENADAS
# -----------------------------------------------------------------------------
# Creamos un mapa {ID → (x, y)} con el depósito como ID 0 en (0,0).
coords = {0: (0.0, 0.0)}
for _, row in df.iterrows():
    coords[row['Cliente ID']] = (row['Coordenada X'], row['Coordenada Y'])

# -----------------------------------------------------------------------------
# 4. FUNCIONES AUXILIARES
# -----------------------------------------------------------------------------
def distancia(p1, p2):
    """
    Calcula la distancia euclidiana entre dos puntos p1 y p2.
    p1, p2: tuplas (x, y) en km.
    Retorna: float, distancia en km.
    """
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

# -----------------------------------------------------------------------------
# 5. ACUMULADORES DE RESULTADOS
# -----------------------------------------------------------------------------
# entregas: lista de dicts con registros detallados de cada visita
# metricas: lista de dicts con resumen diario de cada camión
entregas = []
metricas  = []

# -----------------------------------------------------------------------------
# 6. BUCLE PRINCIPAL: PLANIFICACIÓN DÍA A DÍA
# -----------------------------------------------------------------------------
día_actual = 1
while not df['asignado'].all():
    print(f"--- Planificando día {día_actual} ---")
    
    # 6.1. Inicializar la flota de 4 camiones
    # Cada camión lleva:
    #   'ruta': lista de IDs visitados (arranca en depósito)
    #   'carga': kg actualmente a bordo
    #   'tiempo': min transcurridos desde inicio jornada
    #   'dist' : km recorridos
    camiones = [
        {'ruta': [0], 'carga': 0, 'tiempo': 0.0, 'dist': 0.0}
        for _ in range(4)
    ]

    # 6.2. Para cada camión de la flota
    for idx, camion in enumerate(camiones, start=1):
        ubic = 0  # posición actual del camión (ID de cliente o depósito)

        # 6.3. Loop de salidas y recargas mientras queden clientes factibles
        while True:
            # Filtrar clientes no asignados que quepan en carga restante
            resto = df[~df['asignado']]
            candidatos = resto[resto['Peso (kg)'] + camion['carga'] <= CAPACIDAD_MAX]
            if candidatos.empty:
                break  # No hay más entregas posibles hoy para este camión
            
            # Evaluar coste de servicio para cada candidato:
            # coste = tiempo de ida + T_DESPACHO + tiempo de retorno
            mejor = None  # guardará (cid, coste, t_ida, d_ida)
            for _, row in candidatos.iterrows():
                cid = row['Cliente ID']
                # 6.3.1. Calcular tiempo de ida y retorno al depósito
                d_ida = distancia(coords[ubic], coords[cid])
                t_ida = (d_ida / VEL_MED) * 60
                t_ret = (distancia(coords[cid], coords[0]) / VEL_MED) * 60
                coste = t_ida + T_DESPACHO + t_ret
                
                # Saltar si excede la jornada
                if camion['tiempo'] + coste > T_JORNADA:
                    continue

                # Seleccionar el candidato de menor coste
                if mejor is None or coste < mejor[1]:
                    mejor = (cid, coste, t_ida, d_ida)

            if mejor is None:
                break  # Ningún candidato cabe en el tiempo restante
            
            # 6.3.2. Atender al cliente seleccionado
            cid_sel, coste_sel, t_ida_sel, d_ida_sel = mejor
            # Calcular minutos de llegada y de fin de despacho
            llegada = camion['tiempo'] + t_ida_sel
            salida  = llegada + T_DESPACHO

            # 6.3.3. Registrar en 'entregas'
            entregas.append({
                'día': día_actual,
                'camión': idx,
                'cliente': cid_sel,
                'llegada_min': round(llegada, 1),
                'salida_min':  round(salida,  1),
                'dist_tramo_km': round(d_ida_sel, 2)
            })

            # 6.3.4. Marcar cliente como servido en el DataFrame
            df.loc[
                df['Cliente ID'] == cid_sel,
                ['asignado', 'día_entrega']
            ] = [True, día_actual]

            # 6.3.5. Actualizar estado del camión
            camion['ruta'].append(cid_sel)
            camion['carga']  += int(row['Peso (kg)'])
            camion['tiempo']  = salida
            camion['dist']   += d_ida_sel
            ubic = cid_sel

            # 6.3.6. Recarga intermedia si ya no cabe el siguiente peso mínimo
            pesos_rest = df[~df['asignado']]['Peso (kg)']
            if not pesos_rest.empty and camion['carga'] + pesos_rest.min() > CAPACIDAD_MAX:
                # Volver al depósito
                d_vuelta = distancia(coords[ubic], coords[0])
                t_vuelta = (d_vuelta / VEL_MED) * 60
                camion['tiempo'] += t_vuelta + T_RECARGA
                camion['dist']   += d_vuelta
                camion['ruta'].append(0)
                # Reset de carga y posición
                camion['carga'] = 0
                ubic = 0

        # 6.4. Cerrar la ruta diaria regresando al depósito si es necesario
        if ubic != 0:
            d_final = distancia(coords[ubic], coords[0])
            t_final = (d_final / VEL_MED) * 60
            camion['tiempo'] += t_final
            camion['dist']   += d_final
            camion['ruta'].append(0)

        # 6.5. Registrar métricas diarias de este camión
        metricas.append({
            'día': día_actual,
            'camión': idx,
            'distancia_km': round(camion['dist'], 2),
            'tiempo_min':   round(camion['tiempo'], 1)
        })

    # 6.6. Avanzar al siguiente día
    día_actual += 1

# -----------------------------------------------------------------------------
# 7. CREAR TABLAS ORDENADAS CON PANDAS
# -----------------------------------------------------------------------------
entregas_df = pd.DataFrame(entregas).sort_values(
    ['día','camión','llegada_min']
)[['día','camión','cliente','llegada_min','salida_min','dist_tramo_km']]

metricas_df = pd.DataFrame(metricas).sort_values(
    ['día','camión']
)[['día','camión','distancia_km','tiempo_min']]

# -----------------------------------------------------------------------------
# 8. GENERAR REPORTE EN PDF
# -----------------------------------------------------------------------------
pdf_path = 'reporte_entregas.pdf'
with PdfPages(pdf_path) as pdf:
    # 8.1. Página de entregas
    fig, ax = plt.subplots(figsize=(8.27, 11.69))  # Tamaño A4 en pulgadas
    ax.axis('off')
    tabla_ent = ax.table(
        cellText=[entregas_df.columns.tolist()] + entregas_df.values.tolist(),
        loc='center'
    )
    tabla_ent.auto_set_font_size(False)
    tabla_ent.set_fontsize(6)
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # 8.2. Página de métricas
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis('off')
    tabla_met = ax.table(
        cellText=[metricas_df.columns.tolist()] + metricas_df.values.tolist(),
        loc='center'
    )
    tabla_met.auto_set_font_size(False)
    tabla_met.set_fontsize(8)
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # 8.3. Página de rutas (gráfico X–Y)
    fig, ax = plt.subplots(figsize=(8, 6))
    for idx in entregas_df['camión'].unique():
        seq = (
            [0]
            + entregas_df[entregas_df['camión'] == idx]['cliente'].tolist()
            + [0]
        )
        xs = [coords[i][0] for i in seq]
        ys = [coords[i][1] for i in seq]
        ax.plot(xs, ys, marker='o', label=f'Camión {idx}')
    ax.scatter(0, 0, s=100, marker='s', label='Depósito')
    ax.set_xlabel("X (km)")
    ax.set_ylabel("Y (km)")
    ax.set_title("Rutas de entrega por camión")
    ax.legend()
    ax.grid(True)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

print(f"✅ PDF generado: {pdf_path}")
