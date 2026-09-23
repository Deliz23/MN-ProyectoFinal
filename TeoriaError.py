
import csv
import time
import numpy as np

def mulberry32(semilla):
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
    # numpy hace el redondeo a float32 al convertir el dtype
    return (desviaciones.astype(np.float64) + base).astype(dtype)


#  Métodos de suma 

def suma_directa(arreglo):
    # numpy conserva el dtype (float32 o float64) en cada suma escalar,
    # así que esto ya reproduce la aritmética real de precisión simple
    # o doble, sin necesidad de redondear manualmente como en JS.
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


#  Barrido automático 

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


# Salida: tabla en consola + CSV para la carpeta de resultados

def imprimir_tabla(resultados):
    encabezado = f"{'escala':>8} {'tipo':>8} {'metodo':>8} {'centrado':>9} " \
                 f"{'suma':>22} {'error_rel':>14} {'tiempo_ms':>10} {'estado':>10}"
    print(encabezado)
    print('-' * len(encabezado))
    for r in resultados:
        estado = 'cumple' if r['cumple'] else 'NO cumple'
        print(f"{r['escala']:>8.0e} {r['tipo_dato']:>8} {r['metodo']:>8} "
              f"{'sí' if r['centrado'] else 'no':>9} "
              f"{r['suma']:>22.6f} "
              f"{r['error_rel'] * 100:>13.3e}% {r['tiempo_ms']:>10.2f} {estado:>10}")


def guardar_csv(resultados, ruta):
    campos = ['escala', 'tipo_dato', 'metodo', 'centrado', 'suma', 'referencia',
              'error_abs', 'error_rel', 'tiempo_ms', 'memoria_bytes', 'cumple']
    with open(ruta, 'w', newline='', encoding='utf-8') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(resultados)


if __name__ == '__main__':
    config = {
        'n': 200_000,
        'var_min': 0.01,
        'var_max': 2,
        'semilla': 12345,        
        'escalas': [1e3, 1e6, 1e9],
        'umbral_error': 0.005,     # 0.5%
    }

    resultados = ejecutar_auditoria(config)
    imprimir_tabla(resultados)
    guardar_csv(resultados, 'referencia_resultados.csv')
    print("\nResultados guardados en referencia_resultados.csv")