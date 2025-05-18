# Respuestas

## Para correr el código asegurate de instalar las dependencias que se incluyen en requirements.txt

## 1. ¿Qué clientes fueron asignados a cada camión y bajo qué criterio se hizo la distribución?

### 1.1. Criterio de asignación

El algoritmo utiliza una heurística *nearest-neighbor* **ponderada por tiempo**. En cada paso:

1. **Filtrar candidatos**: sólo se consideran los clientes no atendidos cuyo peso, sumado a la carga actual del camión, no excede `CAPACIDAD_MAX = 15 kg`.
2. **Calcular “coste”** para cada candidato *c* desde la posición actual del camión (*ubic*):

   $$
     \begin{aligned}
       d_{\text{ida}} &= \text{Euclidiana}(\text{coordenadas}(\text{ubic}),\,\text{coordenadas}(c))\\
       t_{\text{ida}} &= \frac{d_{\text{ida}}}{\text{VEL\_MED}} \times 60\\
       d_{\text{retorno}} &= \text{Euclidiana}(\text{coordenadas}(c),\, (0,0))\\
       t_{\text{retorno}} &= \frac{d_{\text{retorno}}}{\text{VEL\_MED}} \times 60\\
       \text{coste}(c) &= t_{\text{ida}} + T_{\text{DESPACHO}} + t_{\text{retorno}}
     \end{aligned}
   $$
3. **Descartar** cualquier candidato cuyo `camión.tiempo + coste(c)` supere la jornada diaria (`T_JORNADA = 420 min`).
4. **Seleccionar** al cliente con **coste mínimo** y asignarlo al camión.
5. **Actualizar**:

   * `camión.ruta.append(c)`
   * `camión.tiempo += t_ida + T_DESPACHO`
   * `camión.carga += peso(c)`
   * `camión.dist += d_ida`
   * `ubic = c`
6. Repetir hasta que no queden candidatos factibles; luego, si aún hay jornada y/o carga, se **recarga intermedia** (vuelta a depósito + `T_RECARGA = 20 min`) y se continua otro loop.

Este criterio combina la cercanía geográfica (distancia euclidiana) con el impacto temporal de ida, despacho y posible retorno, garantizando rutas **rápidas** y factibles dentro de las restricciones.

---

### 1.2. Resultados: Asignación completa

El proceso se repitió **día a día** hasta atender a los 50 clientes. El documento PDF generado contiene, en la **Página 1**, la tabla completa de entregas con la columna `día_entrega`. A modo de ejemplo, aquí se muestran las rutas del **Día 1**:

| Camión | Secuencia de clientes (día 1) | Carga final (kg) | Tiempo empleado (min) |
| :----: | :---------------------------: | :--------------: | :-------------------: |
|    1   |     4 → 43 → 13 → 21 → 47     |        15        |         111,2         |
|    2   |  18 → 28 → 14 → 25 → 10 → 11  |        15        |         132,7         |
|    3   |      6 → 24 → 2 → 27 → 39     |        15        |         142,1         |
|    4   |     30 → 50 → 5 → 42 → 45     |        15        |         172,4         |

En días sucesivos, cada camión reemprendió rutas tras recarga, atendiendo nuevos clientes según el mismo criterio. El balance final por camión y día está tabulado en la **Página 2** del PDF (`metricas_df`).

---

## 2. ¿Todos los clientes fueron atendidos? ¿Quedó algún cliente sin atender?

### 2.1. Planificación single-day vs. multi-día

* **Single-day** (una sola jornada):
  La restricción de tiempo y capacidad provocó que **5 clientes no pudieran caber** en la jornada del Día 1 (por costes de ida+despacho+retorno mayores al tiempo restante).

* **Multi-día** (bucle que repite jornadas):
  El script arranca cada día con flota recargada y tiempo a cero. El bucle `while not df['asignado'].all():` asegura que los clientes no atendidos “pasen” automáticamente al día siguiente.

### 2.2. Resultado final

Gracias a la planificación multi-día, **todos los 50 clientes** fueron atendidos. En la **Página 1** del PDF figuran 50 filas de entregas, cada una con su `día_entrega`. No queda ningún cliente sin servicio al concluir la ejecución.

---

## 3. ¿Cómo se visualizan las rutas (y, en dado caso, los clientes no atendidos) en un gráfico y qué conclusiones pueden extraerse de la solución encontrada?

### 3.1. Visualización

En la **Página 3** del PDF se incluye un gráfico de coordenadas X–Y:

* Cada ruta de cada camión aparece en un color distinto, con marcadores en cada entrega.
* El **depósito** se señala con un cuadrado grande en (0,0).
* Las líneas conectan el orden de servicio, ilustrando los “clusters” de entregas.

Si se produjeran clientes no atendidos (por ejemplo, en una simulación sin multi-día), sus puntos quedarían fuera de las rutas trazadas.

### 3.2. Conclusiones extraídas

1. **Agrupamiento geográfico**

   * El método nearest-neighbor tiende a agrupar clientes próximos, formando sub-rutas locales que minimizan largos desplazamientos.
2. **Eficiencia temporal**

   * Incluir el retorno en el coste permite prever si una entrega al final de ruta impediría regresar a tiempo al depósito.
3. **Impacto de recarga intermedia**

   * La recarga (20 min) introduce “tiempo muerto” pero permite servir más clientes en el mismo día.
4. **Desbalance**

   * Se observa que algunos camiones completan más tramos que otros; esto sugiere que, sin un paso de balanceo previo, la distribución de carga/tiempo no es perfectamente equitativa.

---

## 4. ¿Cómo valoraría el método de planificación de rutas? ¿Identifica una posible mejora?

### 4.1. Valoración del método actual

* **Ventajas**

  * **Simple y rápido** de implementar.
  * Garantiza factibilidad (nunca excede capacidad ni jornada).
  * Se adapta dinámicamente día a día.
* **Limitaciones**

  * **Subóptimo global**: al ser greedy, puede “empantanar” rutas en zonas marginales y dejar clientes lejanos para días posteriores.
  * **Desbalance de flota**: sin un paso previo que agrupe zonas, un camión puede recorrer muchas más kms que otro.

### 4.2. Posible mejora

1. **Clustering previo**

   * Aplicar K-means (o similar) sobre las coordenadas para definir “zonas” geográficas y asignar a cada camión un cluster distinto.
   * Ventaja: balance de clientes y distancias desde el inicio.
2. **Algoritmo de Savings de Clarke–Wright**

   * Parte de rutas individuales, luego las fusiona si reducen costo global.
   * Tiende a soluciones más ajustadas que nearest-neighbor puro.
3. **Metaheurísticas**

   * Simulated Annealing, Algoritmos Genéticos o Búsqueda Tabú podrían efectuar intercambios de clientes entre rutas, mejorando el resultado global a costa de más tiempo de cómputo.

---

> **Conclusión**: la solución heurística implementada cumple los requisitos: asigna todos los clientes, respeta las restricciones y genera un informe completo. Sin embargo, para un uso industrial o con flotas mayores, convendría incorporar una etapa de optimización o clustering previo que mejore la equidad y reduzca la distancia total recorrida.
