## 1. Objetivo general

Este script implementa una solución heurística al **Vehicle Routing Problem (VRP)** con:

* **Capacidad limitada** de cada camión.
* **Jornada diaria** de 7 h (420 min).
* **Tiempos de despacho** fijos al llegar a cada cliente.
* **Recarga intermedia**: el camión puede volver al depósito durante la jornada para vaciarse y reiniciar su ruta.
* **Asignación multi-día**: los clientes que no entren en un día pasan al siguiente.
* **Salida en PDF** con:

  1. Tabla de entregas (día, camión, cliente, hora llegada, hora salida, distancia tramo).
  2. Tabla de métricas (día, camión, distancia total, tiempo total).
  3. Gráfico de rutas (coordenadas X–Y).

---

## 2. Dependencias e importaciones

```python
import pandas as pd                              # Manejo de datos tabulares
import math                                      # Cálculos numéricos (sqrt, hypot, etc.)
import matplotlib.pyplot as plt                  # Graficado de rutas y tablas
from matplotlib.backends.backend_pdf import PdfPages  # Generación de PDF multipágina
```

* **pandas**: carga y manipulación del Excel de clientes, construcción de tablas de resultados.
* **math.hypot**: distancia euclidiana, más estable que sqrt((dx)\*\*2+(dy)\*\*2).
* **matplotlib**:

  * Tablas en páginas PDF
  * Gráfico final de rutas

---

## 3. Parámetros del problema

```python
CAPACIDAD_MAX = 15    # kg máximo que puede llevar cada camión
VEL_MED      = 60    # km/h velocidad media asumida
T_DESPACHO   = 10    # min necesarios para descargar en cada cliente
T_RECARGA    = 20    # min para volver al depósito y vaciar el camión
T_JORNADA    = 7 * 60  # min (7 horas diarias)
```

* **CAPACIDAD\_MAX** y **T\_JORNADA** vienen del enunciado: garantizan que no se excedan pesos ni tiempos.
* **T\_DESPACHO** y **T\_RECARGA** modelan trabajos logísticos fijos.
* **VEL\_MED** permite convertir distancias a tiempo de viaje:

  $$
    \text{tiempo (min)} = \frac{\text{distancia (km)}}{\text{VEL\_MED (km/h)}} \times 60
  $$

---

## 4. Lectura y preparación de datos

```python
# 1. Leer clientes desde Excel
df = pd.read_excel('clientes.xlsx', engine='openpyxl')

# Inicializar columnas de estado
df['asignado']    = False    # ¿Ya fue servido?
df['día_entrega'] = None     # Día en que se sirvió
```

* Usamos **openpyxl** como motor para evitar warnings de `xlrd`.
* Agregamos dos columnas:

  * **asignado**: control booleano
  * **día\_entrega**: para registro multi-día

---

## 5. Diccionario de coordenadas

```python
coords = {0: (0, 0)}  # punto depósito = ID 0
for _, r in df.iterrows():
    coords[r['Cliente ID']] = (r['Coordenada X'], r['Coordenada Y'])
```

* Creamos un dict `{ID → (x,y)}` que facilita:

  * Cálculo de distancias
  * Indexado rápido por cliente

---

## 6. Función de distancia euclidiana

```python
def distancia(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
```

* Basada en:

  $$
    d = \sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}
  $$
* **Origen**: cálculo de distancia aérea entre dos puntos en el plano.

---

## 7. Acumuladores de resultados

```python
entregas = []  # lista de dicts con cada entrega (día, camión, cliente, tiempos, dist tramo)
metricas  = [] # lista de dicts con resumen diario por camión (dist total, tiempo total)
```

* Más tarde los volcamos a `pandas.DataFrame` para tablas y PDF.

---

## 8. Bucle principal por día

```python
día_actual = 1
while not df['asignado'].all():
    # Inicializar 4 camiones al inicio del día...
    # ... lógica de rutas y recargas intermedias ...
    día_actual += 1
```

* **Criterio**: repetimos un “día logístico” mientras queden clientes sin servir.
* Cada iteración:

  1. Reinicia la **flota** con tiempo, distancia y carga a cero.
  2. Para cada camión, ejecuta múltiples “loops” de entrega + posible recarga.
  3. Registra en `entregas` y `metricas` toda la actividad.

---

### 8.1 Inicialización de la flota diaria

```python
camiones = [
    {'ruta': [0], 'carga':0, 'tiempo':0, 'dist':0}
    for _ in range(4)
]
```

* **ruta** arranca en `[0]` (depósito).
* **carga** y **tiempo** en 0.
* **dist** acumula km recorridos.

---

### 8.2 Rutina de un camión

Para cada `camión` (índice `idx`):

1. **ubic** ← 0  (ID del depósito)
2. **while True**:

   * Filtrar **candidatos** no asignados que entren en peso:

     ```python
     rest = df[~df['asignado']]
     cand = rest[rest['Peso (kg)'] + camion['carga'] <= CAPACIDAD_MAX]
     ```
   * Si no hay, **break**.
   * Calcular “coste” para cada candidato:

     $$
       \text{coste} = t_{\text{ida}} + T_{\text{DESPACHO}} + t_{\text{retorno}}
     $$

     donde

     $$
       t_{\text{ida}} = \frac{d(\text{ubic},c)}{\text{VEL\_MED}}\times60,\quad
       t_{\text{retorno}} = \frac{d(c,0)}{\text{VEL\_MED}}\times60
     $$
   * Descartar si excede jornada:
     `camion['tiempo'] + coste > T_JORNADA`
   * Escoger el de menor `coste`.
3. Si no hay candidato válido, **break**.
4. **Registrar la entrega**:

   * `llegada = camion['tiempo'] + t_ida`
   * `salida  = llegada + T_DESPACHO`
   * Añadimos un dict a `entregas` con esos valores.
5. **Actualizar camión**:

   ```python
   camion['ruta'].append(cid)
   camion['carga']  += peso
   camion['tiempo'] += t_ida + T_DESPACHO
   camion['dist']   += d_ida
   ubic = cid
   ```
6. **Marcar cliente asignado** en `df`:

   ```python
   df.loc[df['Cliente ID']==cid, ['asignado','día_entrega']] = [True, día_actual]
   ```
7. **Recarga intermedia**: si el próximo paquete mínimo ya no cabe,

   * Volver al depósito:

     ```python
     d_v = distancia(coords[ubic], coords[0])
     camion['tiempo'] += d_v/VEL_MED*60 + T_RECARGA
     camion['dist']  += d_v
     camion['ruta'].append(0)
     ubic = 0
     camion['carga'] = 0
     ```
8. **Cierre del día**: si el camión no está en depósito,

   * Calcula regreso final y actualiza `tiempo`, `dist`, `ruta`.

---

## 9. Registro de métricas

Al acabar cada camión, añadimos a `metricas`:

```python
metricas.append({
  'día': día_actual,
  'camión': idx,
  'distancia_km': round(camion['dist'],2),
  'tiempo_min':   round(camion['tiempo'],1)
})
```

* Permite ver cuántos km y minutos consumió cada camión cada día.

---

## 10. Preparación de tablas finales

```python
entregas_df = pd.DataFrame(entregas)
entregas_df = entregas_df[
  ['día','camión','cliente','llegada_min','salida_min','dist_tramo_km']
].sort_values(['día','camión','llegada_min'])

metricas_df = pd.DataFrame(metricas)
metricas_df = metricas_df[
  ['día','camión','distancia_km','tiempo_min']
].sort_values(['día','camión'])
```

* **Ordenamos** por día, camión y hora de llegada para facilitar lectura.

---

## 11. Generación del PDF

```python
with PdfPages('reporte_entregas.pdf') as pdf:
    # Página 1: tabla de entregas
    fig, ax = plt.subplots(figsize=(8.27,11.69)); ax.axis('off')
    ax.table(cellText=[entregas_df.columns.tolist()] + entregas_df.values.tolist(),
             loc='center').auto_set_font_size(False); ax.table().set_fontsize(6)
    pdf.savefig(fig); plt.close(fig)

    # Página 2: tabla de métricas (similares pasos, fontsize=8)
    ...

    # Página 3: gráfico de rutas
    ...
```

* **PdfPages**: crea un PDF multipágina.
* Cada **figura** (tabla o gráfico) se guarda con `pdf.savefig(fig)`.
* Usamos tamaño **A4** (8.27×11.69 in).

---

## 12. Punto de partida y futuras extensiones

* El **pseudocódigo** original se traduce 1:1 en esta implementación.
* La **heurística** es nearest-neighbor con chequeo de retorno.
* **Extensiones posibles**:

  * Ajustar criterio de selección (p.ej. usar “mayor carga” o solver exacto).
  * Incorporar ventanas de tiempo por cliente.
  * Optimizar balance de rutas con clustering previo.
  * Añadir informes gráficos más detallados (heatmaps, histograma de tiempos).

# Explicación Detallada de Todas las Fórmulas y Cálculos

A continuación encontrarás **todas** las fórmulas empleadas en el algoritmo y en el modelo, explicadas **paso a paso** y con ejemplos de para qué sirven y cómo se incorporan al código. Imagina que partes sin conocimiento previo:   cada ecuación, cada constante, cada paso de cálculo quedará justificado.

---

## 1. Distancia Euclidiana

### Fórmula

$$
d_{ij} \;=\; \sqrt{(x_i - x_j)^2 \;+\;(y_i - y_j)^2}
$$

* **¿Qué mide?**
  La distancia “en línea recta” entre dos puntos $(x_i,y_i)$ y $(x_j,y_j)$ en un plano cartesiano.
* **¿Por qué la usamos?**
  Representa la distancia mínima posible que recorrería un camión entre dos ubicaciones sin desvíos.
* **Contexto en el código**:

  ```python
  def distancia(p1, p2):
      # p1=(x_i,y_i), p2=(x_j,y_j)
      return math.hypot(p1[0]-p2[0], p1[1]-p2[1])
  ```
* **Ejemplo numérico**:
  Cliente A en $(-2.6, 30.0)$ y Cliente B en $(6.1, -2.9)$:

  $$
    d = \sqrt{(-2.6 - 6.1)^2 +(30.0 +2.9)^2}
      = \sqrt{(-8.7)^2 +(32.9)^2}
      \approx \sqrt{75.7 + 1082.4}
      \approx \sqrt{1158.1}
      \approx 34.0\text{ km}
  $$

---

## 2. Conversión de Distancia a Tiempo de Viaje

### Fórmula

$$
t_\text{viaje} \;=\; \frac{d}{v}\times 60
$$

* **Dónde**:

  * $d$ = distancia (km).
  * $v$ = velocidad media (km/h).
  * $\times60$ convierte horas a minutos.
* **¿Para qué sirve?**
  Traducir distancia recorrida en tiempo efectivo que el camión tarda en moverse de un punto a otro.
* **Parámetro en el código**:

  ```python
  t_ida = distancia(...) / VEL_MED * 60
  ```
* **Ejemplo**:
  Con $d=34.0$ km y $v=60$ km/h:

  $$
    t = \frac{34.0}{60}\times60 = 34.0\text{ min}
  $$

---

## 3. Tiempo de Despacho Fijo

### Constante

$$
T_\text{DESPACHO} = 10\ \text{min}
$$

* **¿Qué representa?**
  El tiempo que tarda el conductor en descargar el paquete en cada cliente, independientemente de su ubicación o peso.
* **¿Dónde se suma?**
  Cada vez que el camión “atierra” en un cliente, al tiempo de viaje se añade este bloque fijo:

  ```python
  camion['tiempo'] += t_ida + T_DESPACHO
  ```
* **Motivo**:
  Modelar el proceso de manipulación de mercancía, que no depende de la distancia sino de la operación en el punto.

---

## 4. Tiempo de Retorno Estimado

### Fórmula

$$
t_\text{retorno} \;=\; \frac{d_{c\to0}}{v}\times60
$$

* $d_{c\to0}$: distancia euclidiana del cliente actual de vuelta al depósito (0,0).
* Modela el **tiempo mínimo** que requiere el camión para regresar a la base, necesario para garantizar que no exceda la jornada.

---

## 5. Función “Coste” para Selección de Cliente

### Fórmula

$$
\text{coste}(c) \;=\; t_\text{ida} \;+\; T_\text{DESPACHO} \;+\; t_\text{retorno}
$$

* **¿Por qué?**
  Busca el siguiente cliente que suponga **el menor tiempo total extra** si se atiende ahora (incluye ida, despacho y luego la hipotética vuelta al depósito).
* **Implementación**:

  ```python
  coste = t_ida + T_DESPACHO + t_ret
  ```
* **Lógica**: al minimizar este coste, se reduce el riesgo de “quedarse sin tiempo” más adelante.

---

## 6. Capacidad de Carga y Restricción de Peso

### Constante

$$
\text{CAPACIDAD\_MAX} = 15\ \text{kg}
$$

* **¿Dónde se aplica?**
  Antes de considerar un cliente *c* para el siguiente punto de la ruta, filtramos:

  ```python
  candidatos = df[
    (~df['asignado']) &
    (df['Peso (kg)'] + camion['carga'] <= CAPACIDAD_MAX)
  ]
  ```
* **Propósito**:
  Asegurar que el camión no exceda su límite de peso en **ningún momento** de la ruta.

---

## 7. Jornada Laboral y Límites de Tiempo

### Constante

$$
T_\text{JORNADA} = 7 \times 60 = 420\ \text{min}
$$

* Representa las 7 horas efectivas de conducción y entregas diarias (descontada 1 h de preparación).
* Antes de seleccionar un candidato, comprobamos:

  ```python
  if camion['tiempo'] + coste > T_JORNADA:
      # descartar candidato
  ```
* Evita que el camión inicie un tramo que no podría completar (incluyendo el retorno).

---

## 8. Recarga Intermedia

### Proceso y Fórmulas

Cuando la **carga acumulada** + **peso mínimo restante** excede `CAPACIDAD_MAX`, se fuerza un **cycle** de recarga:

1. **Tiempo de vuelta al depósito**:

   $$
     t_\text{vuelta} = \frac{d_{\text{ubic→0}}}{v}\times60
   $$
2. **Tiempo de recarga** (vaciar camión):

   $$
     T_\text{RECARGA} = 20\ \text{min}
   $$
3. **Actualización**:

   ```python
   camion['tiempo'] += t_vuelta + T_RECARGA
   camion['dist']   += d_vuelta
   camion['ruta'].append(0)
   camion['carga']  = 0
   ubic = 0
   ```

* **Por qué**:
  Permite que un camión complete más de un “viaje” en la misma jornada, maximizando el uso de las 7 h.

---

## 9. Registro y Ordenación de Resultados

### Tablas resultantes

* **entregas\_df**: columnas

  * `día`, `camión`, `cliente`
  * `llegada_min`, `salida_min`
  * `dist_tramo_km`
* **metricas\_df**: columnas

  * `día`, `camión`
  * `distancia_km`, `tiempo_min`

Se **ordenan** por:

```python
entregas_df.sort_values(['día','camión','llegada_min'])
metricas_df.sort_values(['día','camión'])
```

---

## 10. Generación de PDF

1. **Tablas**:

   * Se usa `ax.table(...)` de Matplotlib para insertar datos en forma tabular en la primera y segunda página.
2. **Gráfico de rutas**:

   * Tercera página, ploteamos (x,y) de cada secuencia de ruta.
   * `plt.plot(xs, ys, marker='o')` conecta puntos en el orden visitado.

---

### Resumen conceptual

| Concepto           | Fórmula / Valor                       | Objetivo                                        |
| ------------------ | ------------------------------------- | ----------------------------------------------- |
| Dist. euclidiana   | $\sqrt{\Delta x^2 + \Delta y^2}$      | Medir distancia mínima entre dos puntos         |
| Tiempo de viaje    | $\tfrac{d}{v}\times60$                | Convertir km recorridos a minutos de conducción |
| Tiempo de despacho | $T_{\text{DESPACHO}}=10$ min          | Modelar operación de descarga en destino        |
| Coste candidato    | $t_\text{ida} + T_d + t_{\text{ret}}$ | Selección greedy del siguiente cliente          |
| Capacidad          | $15$ kg                               | Restricción física de carga del vehículo        |
| Jornada            | $420$ min                             | Límite diario de operación (7 h conduciendo)    |
| Recarga intermedia | $t_{\text{vuelta}} + 20$ min          | Permitir “loops” múltiples en la misma jornada  |

# Documento de Preguntas Frecuentes y Posibles Cambios

---

## I. Preguntas que el profesor podría hacer sobre el código

### 1. ¿Cómo se asegura que ningún camión exceda la jornada laboral de 7 h?

**Respuesta:**

* Cada vez que se calcula el “coste” de atender a un cliente (ida + despacho + posible retorno), se comprueba

  ```python
  if camion['tiempo'] + coste > T_JORNADA:
      continue  # descarta a ese candidato
  ```
* De este modo nunca se inicia un tramo que haría que `camion['tiempo']` supere los 420 min.

---

### 2. ¿Cuál es la lógica para la recarga intermedia y por qué es necesaria?

**Respuesta:**

* Tras cada entrega comprobamos si **el siguiente paquete mínimo** cabría en la carga restante.
* Si no cabe, forzamos que el camión regrese al depósito y pase `T_RECARGA = 20 min` descargando su carga:

  ```python
  camion['tiempo'] += t_vuelta + T_RECARGA
  camion['ruta'].append(0)
  camion['carga'] = 0
  ubic = 0
  ```
* Esto permite a un mismo camión realizar **múltiples “loops”** dentro de las 7 h en lugar de una sola salida.

---

### 3. ¿Cómo se registra el día en que se entrega a cada cliente?

**Respuesta:**

* Se añade una columna `día_entrega` al DataFrame antes de empezar:

  ```python
  df['día_entrega'] = None
  ```
* Al asignar un cliente:

  ```python
  df.loc[df['Cliente ID']==cid, ['asignado','día_entrega']] = [True, día_actual]
  ```
* De esta forma, al final cada fila de `entregas_df` lleva la fecha (número de día) en que se sirvió.

---

### 4. ¿Por qué usamos distancia euclidiana y cómo se calcula?

**Respuesta:**

* Elegimos la **distancia euclidiana** para modelar el recorrido en línea recta, que es la más sencilla y habitual en VRP.
* Se calcula con

  $$
    d = \sqrt{(x_i - x_j)^2 + (y_i - y_j)^2}
  $$

  y en Python:

  ```python
  def distancia(p1, p2):
      return math.hypot(p1[0]-p2[0], p1[1]-p2[1])
  ```

---

### 5. ¿Qué librerías generan el PDF y cómo se formatea?

**Respuesta:**

* Usamos `matplotlib.backends.backend_pdf.PdfPages` para un PDF multipágina.
* Cada página se crea con un `fig, ax = plt.subplots(...)`, se inserta una tabla o un gráfico, y se guarda con

  ```python
  pdf.savefig(fig, bbox_inches='tight')
  plt.close(fig)
  ```

---

### 6. ¿Qué ocurre si un cliente queda muy lejos y no cabe ni en carga ni en jornada?

**Respuesta:**

* No aparecerá en el ciclo de ese día porque:

  * Si el **peso** excede capacidad, se filtra en

    ```python
    candidatos = resto[resto['Peso (kg)'] + camion['carga'] <= CAPACIDAD_MAX]
    ```
  * Si el **coste** excede jornada, se descarta en el bucle de coste.
* Pero como usamos planificación **multi-día**, el cliente vuelve a considerarse al día siguiente, siempre y cuando el tiempo restante en ese día se reinicie a 420 min.

---

### 7. ¿Cómo maneja el script la terminación cuando todos los clientes han sido servidos?

**Respuesta:**

* El bucle principal es:

  ```python
  while not df['asignado'].all():
      # Planificar un día más...
  ```
* Cuando `df['asignado']` es `True` para los 50 clientes, la condición falla y se sale del bucle.

---

## II. Posibles cambios que el profesor podría proponer y cómo adaptar el código

### 1. *“Agrega un nuevo camión y verifica cómo cambian las rutas”*

* **Qué cambiar**: en el paso de inicialización de flota, modificar el número de camiones:

  ```diff
  - camiones = [{'ruta':[0], 'carga':0, 'tiempo':0, 'dist':0} for _ in range(4)]
  + camiones = [{'ruta':[0], 'carga':0, 'tiempo':0, 'dist':0} for _ in range(5)]
  ```
* **Efecto**: habrá un camión extra que podrá absorber más clientes por día; las funciones de bucles y métricas se ajustan automáticamente.

---

### 2. *“Cambia la velocidad promedio a 40 km/h y observa el impacto”*

* **Qué cambiar**: la constante `VEL_MED`:

  ```diff
  - VEL_MED = 60
  + VEL_MED = 40
  ```
* **Efecto**: aumentan los tiempos de ida y retorno, por lo que habrá menos entregas por jornada y el número de días requeridos podría subir.

---

### 3. *“Modifica la jornada a 8 horas efectivas en lugar de 7 h”*

* **Qué cambiar**: la constante `T_JORNADA`:

  ```diff
  - T_JORNADA = 7 * 60
  + T_JORNADA = 8 * 60
  ```
* **Efecto**: mayor tiempo disponible—más clientes servidos por día, probablemente reduciendo el total de días.

---

### 4. *“Aumenta el tiempo de despacho a 15 min por cliente”*

* **Qué cambiar**: la constante `T_DESPACHO`:

  ```diff
  - T_DESPACHO = 10
  + T_DESPACHO = 15
  ```
* **Efecto**: aumenta el coste de cada parada, reduciendo el número de entregas diarias y posiblemente incrementando la necesidad de recargas intermedias.

---

### 5. *“Usa distancia Manhattan en lugar de Euclidiana”*

* **Qué cambiar**: redefinir la función `distancia`:

  ```diff
  - def distancia(p1, p2):
  -     return math.hypot(p1[0]-p2[0], p1[1]-p2[1])
  + def distancia(p1, p2):
  +     return abs(p1[0]-p2[0]) + abs(p1[1]-p2[1])
  ```
* **Efecto**: mide distancia como “recorrido en cuadrícula” (ideal si la ciudad tiene avenidas ortogonales). Cambia completamente la forma en que se elige el “cliente más cercano”.

---

### 6. *“Incorpora ventanas de tiempo por cliente (time windows)”*

* **Qué implica**:

  1. Añadir dos columnas a `df`: `ventana_inicio` y `ventana_fin`.
  2. Al calcular `coste`, incluir:

     ```python
     if llegada < ventana_inicio:
         # esperar hasta ventana_inicio
         t_espera = ventana_inicio - llegada
     else:
         t_espera = 0
     salida = llegada + t_espera + T_DESPACHO
     ```
  3. Descartar candidatos si `salida > ventana_fin`.
* **Ejemplo de código**:

  ```python
  df['ventana_inicio'] = [...]
  df['ventana_fin']    = [...]
  # Dentro del bucle:
  llegada = camion['tiempo'] + t_ida
  t_espera = max(0, row['ventana_inicio'] - llegada)
  salida = llegada + t_espera + T_DESPACHO
  if salida > row['ventana_fin']:
      continue
  ```

---

### 7. *“Exporta el reporte también en formato CSV en lugar de PDF”*

* **Qué agregar** tras generar los DataFrames ordenados:

  ```python
  entregas_df.to_csv('entregas.csv', index=False)
  metricas_df.to_csv('metricas.csv', index=False)
  ```

---
