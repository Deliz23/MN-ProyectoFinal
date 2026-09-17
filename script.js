function ejecutarSimulacion() {
    // 1. Obtener datos de la interfaz
    let T0 = parseFloat(document.getElementById('t0').value);
    let Tamb = parseFloat(document.getElementById('tamb').value);
    let k = parseFloat(document.getElementById('k').value);
    let h = parseFloat(document.getElementById('h').value);
    let tFinal = parseFloat(document.getElementById('tfinal').value);

    let divEstado = document.getElementById('mensaje-estado');
    let divTabla = document.getElementById('contenedor-tabla');

    // 2. Validación de Entradas de Dominio
    if (k <= 0 || tFinal <= 0 || h <= 0) {
        divEstado.className = "estado-box error";
        divEstado.innerHTML = "<strong>Error:</strong> Los parámetros <i>k</i>, <i>h</i> y el <i>tiempo final</i> deben ser mayores que 0.";
        divTabla.innerHTML = "";
        return;
    }

    // 3. Verificación de Estabilidad Numérica (1 - hk)
    let factor = Math.abs(1 - h * k);
    if (factor >= 1) {
        divEstado.className = "estado-box advertencia";
        divEstado.innerHTML = `<strong>⚠️ Advertencia de Inestabilidad:</strong> Con $h = ${h}$ y $k = ${k}$, $|1 - hk| = ${factor.toFixed(2)} \ge 1$. El método oscilará de forma inestable (artefacto numérico).`;
    } else {
        divEstado.className = "estado-box exito";
        divEstado.innerHTML = "<strong>✅ Cálculo Exitoso:</strong> La simulación es numéricamente estable.";
    }

    // Volver a procesar fórmulas LaTeX dinámicas si MathJax está presente
    if (window.MathJax) MathJax.typesetPromise();

    // 4. Algoritmo de Euler Explícito y Tabla de Iteraciones
    let t = 0;
    let T = T0;
    let paso = 0;

    let htmlTabla = `
        <h3>Tabla de Iteraciones</h3>
        <table>
            <thead>
                <tr>
                    <th>Paso (n)</th>
                    <th>Tiempo $t_n$ (min)</th>
                    <th>Temperatura $T_n$ (°C)</th>
                    <th>Derivada $T'$ (°C/min)</th>
                </tr>
            </thead>
            <tbody>
    `;

    while (t <= tFinal) {
        let dTdt = -k * (T - Tamb);
        
        htmlTabla += `
            <tr>
                <td>${paso}</td>
                <td>${t.toFixed(2)}</td>
                <td>${T.toFixed(4)}</td>
                <td>${dTdt.toFixed(4)}</td>
            </tr>
        `;

        let hActual = Math.min(h, tFinal - t);
        if (hActual <= 0) break;

        T = T + hActual * dTdt;
        t += hActual;
        paso++;
    }

    htmlTabla += `</tbody></table>`;
    divTabla.innerHTML = htmlTabla;

    if (window.MathJax && window.MathJax.typesetPromise) {
        window.MathJax.typesetPromise();
    }
}