# MN-ProyectoFinal
# Teoria de Errores

## Descripción

Este proyecto implementa una auditoría de precisión numérica para analizar el comportamiento de diferentes métodos de suma utilizando números en punto flotante.

Se comparan tres métodos:

* Suma directa.
* Suma de Kahan.
* Suma centrada.

Las pruebas se realizan utilizando los tipos de datos `float32` y `float64`, considerando diferentes escalas de valores.

El objetivo es analizar el error numérico producido durante las operaciones de suma y observar cómo influyen la escala de los datos, el tipo de dato y el método utilizado.

## Métodos implementados

### Suma directa

Realiza la suma de los elementos del arreglo de manera secuencial, acumulando cada valor en una variable.

### Suma de Kahan

Utiliza una variable de compensación para reducir el error de redondeo producido durante la acumulación de los valores.

### Suma centrada

Resta previamente una escala base a los valores antes de realizar la suma. Después de realizar la suma de las desviaciones, se vuelve a incorporar la contribución de la escala base.

## Requisitos

Para ejecutar el programa se necesita:

* Python 
* NumPy
* Matplotlib

## Instalación

Instalar las dependencias mediante:

```bash
pip install numpy matplotlib
```

## Ejecución

Ejecutar el archivo principal mediante:

```bash
python TeoriaError.py
```

También puede ejecutarse desde un entorno como Jupyter Notebook o Visual Studio Code.

## Configuración

Los principales parámetros del experimento se encuentran en la configuración del programa:

```python
config = {
    'n': 200_000,
    'var_min': 0.01,
    'var_max': 2,
    'semilla': 12345,
    'escalas': [1e3, 1e6, 1e9],
    'umbral_error': 0.005,
}
```

Estos parámetros representan:

* `n`: cantidad de muestras utilizadas.
* `var_min`: variación mínima.
* `var_max`: variación máxima.
* `semilla`: valor utilizado para generar los mismos datos de manera reproducible.
* `escalas`: escalas base utilizadas en las pruebas.
* `umbral_error`: máximo error relativo permitido. En este caso corresponde al 0.5%.

## Resultados generados

Al ejecutar el programa se generan:

### Archivo CSV

```text
referencia_resultados.csv
```

Contiene los resultados obtenidos para cada combinación de escala, tipo de dato, método y centrado.

### Gráfico de error relativo

```text
referencia_grafico.png
```

Muestra el error relativo en función de la escala base.

### Gráfico de acumulación del error

```text
figura_error_vs_muestras.png
```

Muestra cómo cambia el error a medida que aumenta el número de muestras acumuladas.

## Métricas

El programa registra:

* Error absoluto.
* Error relativo.
* Tiempo de ejecución.
* Memoria asociada a los datos.
* Cumplimiento del umbral de error.

## Estructura del proyecto

```text
proyecto/
│
├── codigo.py
├── referencia_resultados.csv
├── referencia_grafico.png
├── figura_error_vs_muestras.png
└── README.md
```

## Reproducibilidad

El programa utiliza una semilla fija (`12345`) para generar las desviaciones pseudoaleatorias. Esto permite repetir el experimento utilizando los mismos datos de entrada y comparar los resultados obtenidos.

## Conclusión

El programa permite comparar diferentes estrategias de suma y observar el efecto de la representación en punto flotante sobre la precisión numérica. Los resultados permiten analizar las diferencias entre `float32` y `float64`, así como el efecto de utilizar compensación mediante Kahan y centrado de los datos.
