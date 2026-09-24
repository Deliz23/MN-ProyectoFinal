
import csv
import time
import numpy as np


# ============================================================
# 1. Generador pseudoaleatorio 
# ============================================================

def mulberry32(semilla):
    """Puerto exacto de la función mulberry32 usada en script.js.
    Se enmascara con & 0xFFFFFFFF en cada paso para simular el
    desbordamiento de enteros de 32 bits que JavaScript hace de forma
    nativa con sus operadores >>> y |0."""
    estado = semilla & 0xFFFFFFFF

    def siguiente():
        nonlocal estado
        estado = (estado + 0x6D2B79F5) & 0xFFFFFFFF
        t = estado
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t2 = (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        t = (t2 ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return siguiente


def generar_desviaciones(n, var_min, var_max, semilla):
    aleatorio = mulberry32(semilla)
    desviaciones = np.empty(n, dtype=np.float64)
    for i in range(n):
        magnitud = var_min + aleatorio() * (var_max - var_min)
        signo = -1.0 if aleatorio() < 0.5 else 1.0
        desviaciones[i] = signo * magnitud
    return desviaciones


def construir_latencias(desviaciones, base, tipo_dato):
    dtype = np.float32 if tipo_dato == 'float32' else np.float64
    # numpy hace el redondeo a float32 al convertir el dtype, igual que
    # Float32Array en JavaScript.
    return (desviaciones.astype(np.float64) + base).astype(dtype)


# ============================================================
# 2. Métodos de suma 
# ============================================================

def suma_directa(arreglo):
    # numpy conserva el dtype (float32 o float64) en cada suma escalar
    tipo = arreglo.dtype
    suma = tipo.type(0)
    for x in arreglo:
        suma = suma + x
    return suma


def suma_kahan(arreglo):
    tipo = arreglo.dtype
    suma = tipo.type(0)
    compensacion = tipo.type(0)
    for x in arreglo:
        y = x - compensacion
        t = suma + y
        compensacion = (t - suma) - y
        suma = t
    return suma


def suma_centrada(arreglo, base, metodo):
    dtype = arreglo.dtype
    centrado = (arreglo.astype(np.float64) - base).astype(dtype)
    suma_del_centrado = suma_kahan(centrado) if metodo == 'kahan' else suma_directa(centrado)
    return float(suma_del_centrado) + base * len(arreglo)


def suma_referencia(arreglo, inicio=0, fin=None):
    """Suma por pares (pairwise) en float64: mismo criterio de corte
    (bloques de 512) que sumaReferencia en script.js."""
    if fin is None:
        fin = len(arreglo)
    n = fin - inicio
    if n <= 512:
        return float(np.sum(arreglo[inicio:fin], dtype=np.float64))
    medio = inicio + n // 2
    return suma_referencia(arreglo, inicio, medio) + suma_referencia(arreglo, medio, fin)


# ============================================================
# 3. Barrido automático 
# ============================================================

def ejecutar_auditoria(config):
    n = config['n']
    desviaciones = generar_desviaciones(n, config['var_min'], config['var_max'], config['semilla'])
    resultados = []

    for base in config['escalas']:
        datos_referencia = construir_latencias(desviaciones, base, 'float64')
        referencia = suma_referencia(datos_referencia)

        for tipo_dato in ['float32', 'float64']:
            bytes_por_elemento = 4 if tipo_dato == 'float32' else 8
            datos = construir_latencias(desviaciones, base, tipo_dato)

            for metodo in ['directa', 'kahan']:
                for centrar in [False, True]:
                    t0 = time.perf_counter()
                    if centrar:
                        suma = suma_centrada(datos, base, metodo)
                    else:
                        suma = float(suma_kahan(datos) if metodo == 'kahan' else suma_directa(datos))
                    t1 = time.perf_counter()

                    error_abs = abs(suma - referencia)
                    error_rel = error_abs / abs(referencia)

                    resultados.append({
                        'escala': base, 'tipo_dato': tipo_dato, 'metodo': metodo,
                        'centrado': centrar, 'suma': suma, 'referencia': referencia,
                        'error_abs': error_abs, 'error_rel': error_rel,
                        'tiempo_ms': (t1 - t0) * 1000,
                        'memoria_bytes': n * bytes_por_elemento,
                        'cumple': error_rel <= config['umbral_error'],
                    })
    return resultados


# ============================================================
# 4. Salidas: tabla general, tabla por tipo de dato, CSV,
#    gráfico error relativo vs. escala, y texto explicativo
# ============================================================

def imprimir_tabla(resultados):
    encabezado = f"{'escala':>8} {'tipo':>8} {'metodo':>8} {'centrado':>9} " \
                 f"{'error_rel':>14} {'tiempo_ms':>10} {'estado':>10}"
    print(encabezado)
    print('-' * len(encabezado))
    for r in resultados:
        estado = 'cumple' if r['cumple'] else 'NO cumple'
        print(f"{r['escala']:>8.0e} {r['tipo_dato']:>8} {r['metodo']:>8} "
              f"{'sí' if r['centrado'] else 'no':>9} "
              f"{r['error_rel'] * 100:>13.3e}% {r['tiempo_ms']:>10.2f} {estado:>10}")


def imprimir_tabla_por_tipo(resultados):
    """Requisito explícito de la guía: 'tabla por tipo de dato'."""
    encabezado = f"{'escala':>8} {'metodo':>8} {'centrado':>9} {'error_rel':>14} " \
                 f"{'tiempo_ms':>10} {'estado':>10}"
    for tipo in ['float32', 'float64']:
        print(f"\n--- {tipo} ---")
        print(encabezado)
        print('-' * len(encabezado))
        for r in resultados:
            if r['tipo_dato'] != tipo:
                continue
            estado = 'cumple' if r['cumple'] else 'NO cumple'
            print(f"{r['escala']:>8.0e} {r['metodo']:>8} {'sí' if r['centrado'] else 'no':>9} "
                  f"{r['error_rel'] * 100:>13.3e}% {r['tiempo_ms']:>10.2f} {estado:>10}")


def guardar_csv(resultados, ruta):
    campos = ['escala', 'tipo_dato', 'metodo', 'centrado', 'suma', 'referencia',
              'error_abs', 'error_rel', 'tiempo_ms', 'memoria_bytes', 'cumple']
    with open(ruta, 'w', newline='', encoding='utf-8') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(resultados)


def graficar_resultados(resultados, ruta):
    """Gráfico error relativo (%) vs. escala base, una línea por
    combinación de tipo de dato + método + centrado. Ejes log-log
    porque el error relativo cambia varios órdenes de magnitud entre
    escalas, y se marca el umbral de 0.5% como referencia visual."""
    import matplotlib.pyplot as plt

    series = {}
    for r in resultados:
        clave = (r['tipo_dato'], r['metodo'], r['centrado'])
        serie = series.setdefault(clave, {'x': [], 'y': []})
        serie['x'].append(r['escala'])
        serie['y'].append(max(r['error_rel'] * 100, 1e-12))  # evita log(0)

    color_por_tipo = {'float32': 'tab:red', 'float64': 'tab:blue'}
    linea_por_metodo = {'directa': '-', 'kahan': '--'}
    marcador_por_centrado = {False: 'o', True: 's'}

    plt.figure(figsize=(7.5, 5))
    for (tipo, metodo, centrado), serie in series.items():
        orden = sorted(range(len(serie['x'])), key=lambda i: serie['x'][i])
        x = [serie['x'][i] for i in orden]
        y = [serie['y'][i] for i in orden]
        etiqueta = f"{tipo} · {metodo} · {'centrado' if centrado else 'crudo'}"
        plt.plot(x, y, marker=marcador_por_centrado[centrado],
                  linestyle=linea_por_metodo[metodo], color=color_por_tipo[tipo],
                  alpha=0.85, label=etiqueta)

    plt.axhline(0.5, color='black', linestyle=':', linewidth=1, label='Umbral 0.5%')
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Escala base (μs)')
    plt.ylabel('Error relativo (%)')
    plt.title('Error relativo vs. escala — auditor de precisión (Lab 01)')
    plt.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1.02, 1))
    plt.tight_layout()
    plt.savefig(ruta, dpi=150)
    plt.close()


def generar_explicacion(resultados):
    """Explicación de la pérdida de significancia + recomendación
    técnica, calculada a partir de los resultados reales (no un texto
    fijo)."""
    fallos_sin_centrar = [r for r in resultados if not r['cumple'] and not r['centrado']]
    fallos_centrados = [r for r in resultados if not r['cumple'] and r['centrado']]
    fallos_float32_directa = [r for r in resultados if not r['cumple']
                               and r['tipo_dato'] == 'float32' and r['metodo'] == 'directa']

    texto = [
        "Pérdida de significancia: cuando la escala base (10^3 a 10^9 microsegundos) supera "
        "ampliamente la variación medida (0.01 a 2 microsegundos), el redondeo al representar "
        "cada dato absorbe las cifras que corresponden a la variación real, antes incluso de "
        "sumar nada. El error relativo del TOTAL puede verse pequeño (se mide contra una suma "
        "enorme) aunque el 100% de la señal de interés se haya perdido."
    ]
    if fallos_float32_directa:
        texto.append(
            "Se confirma en float32 con suma directa sin centrar: la mantisa de 23 bits no "
            "alcanza para representar simultáneamente la escala base y la variación en las "
            "escalas altas."
        )
    if fallos_sin_centrar and not fallos_centrados:
        texto.append(
            "Centrar los datos (restar la escala base antes de sumar) elimina todos los fallos "
            "observados: confirma que el problema es de representación, no de los datos en sí."
        )
    elif fallos_centrados:
        texto.append(
            "Incluso centrando, algunas combinaciones no bajan del umbral; conviene usar "
            "float64 para esos casos en vez de float32."
        )
    texto.append(
        "Recomendación técnica: usar float64 en producción siempre que la memoria lo permita. "
        "Si float32 es obligatorio por espacio, centrar los datos resuelve la mayoría de los "
        "casos con costo casi nulo; Kahan es la opción de respaldo cuando el centrado no es "
        "posible, a cambio de aproximadamente el doble de tiempo de cómputo por la compensación "
        "en cada iteración."
    )
    return "\n".join(texto)



def grafico_error_vs_muestras(desviaciones, base, ruta, num_puntos=30):
    """Gráfico complementario al de graficar_resultados: error relativo (%)
    frente al número de muestras acumuladas (N), a escala base fija.
    Muestra cómo crece el error de la suma directa en float32 a medida
    que el acumulador gana magnitud, y cómo la compensación de Kahan lo
    mantiene acotado. Esta es la evidencia directa de 'acumulación de
    redondeo' (punto 4 del procedimiento obligatorio de la guía),
    distinta de la absorción/cancelación por escala que muestra
    graficar_resultados."""
    import matplotlib.pyplot as plt

    n = len(desviaciones)
    puntos = np.unique(np.round(np.logspace(2, np.log10(n), num_puntos)).astype(int))
    puntos = [p for p in puntos if 0 < p <= n]
    if puntos[-1] != n:
        puntos.append(n)
    checkpoints = set(puntos)

    acumulador_directa = np.float32(0)
    acumulador_kahan = np.float32(0)
    compensacion = np.float32(0)
    acumulador_referencia = 0.0  # float64 corrido, referencia suficiente a este N

    xs, errores_directa, errores_kahan = [], [], []

    for i in range(n):
        v32 = np.float32(base + desviaciones[i])
        v64 = base + desviaciones[i]

        acumulador_directa = acumulador_directa + v32

        y = v32 - compensacion
        t = acumulador_kahan + y
        compensacion = (t - acumulador_kahan) - y
        acumulador_kahan = t

        acumulador_referencia += v64

        if (i + 1) in checkpoints:
            er_directa = abs(float(acumulador_directa) - acumulador_referencia) / acumulador_referencia * 100.0
            er_kahan = abs(float(acumulador_kahan) - acumulador_referencia) / acumulador_referencia * 100.0
            xs.append(i + 1)
            errores_directa.append(max(er_directa, 1e-12))
            errores_kahan.append(max(er_kahan, 1e-12))

    plt.figure(figsize=(8, 5))
    plt.plot(xs, errores_directa, 'r-o', markersize=4, label='float32 · suma directa')
    plt.plot(xs, errores_kahan, 'g-s', markersize=4, label='float32 · suma de Kahan')
    plt.axhline(0.5, color='black', linestyle='--', label='Umbral 0.5%')
    plt.xscale('log')
    plt.yscale('log')
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    plt.xlabel('Número de muestras acumuladas (N)')
    plt.ylabel('Error relativo (%)')
    plt.title(f'Acumulación de redondeo — base = {base:.0e} μs')
    plt.legend()
    plt.tight_layout()
    plt.savefig(ruta, dpi=150)
    plt.close()


if __name__ == '__main__':
    config = {
        'n': 200_000,
        'var_min': 0.01,
        'var_max': 2,
        'semilla': 12345,          # misma semilla que script.js
        'escalas': [1e3, 1e6, 1e9],
        'umbral_error': 0.005,     # 0.5%
    }

    resultados = ejecutar_auditoria(config)

    print("=== Tabla general ===")
    imprimir_tabla(resultados)

    print("\n=== Tabla por tipo de dato ===")
    imprimir_tabla_por_tipo(resultados)

    guardar_csv(resultados, 'referencia_resultados.csv')
    print("\nResultados guardados en referencia_resultados.csv")

    graficar_resultados(resultados, 'referencia_grafico.png')
    print("Gráfico (error vs. escala base) guardado en referencia_grafico.png")

    desviaciones = generar_desviaciones(config['n'], config['var_min'], config['var_max'], config['semilla'])
    grafico_error_vs_muestras(desviaciones, 1e6, 'figura_error_vs_muestras.png')
    print("Gráfico (error vs. N acumulado) guardado en figura_error_vs_muestras.png")

    print("\n=== Explicación de la pérdida de significancia y recomendación técnica ===")
    print(generar_explicacion(resultados))
