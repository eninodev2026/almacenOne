// app/front/inventario/inventario.js
// Usa las funciones de ..\api.js (cargarBodegas, buscarInventario, etc.)

const inpBuscar = document.getElementById("buscar");
const spinner = document.getElementById("spinner");
const btnMostrarFiltros = document.getElementById("btnMostrarFiltros");
const iconoFiltros = document.getElementById("iconoFiltros");
const filtrosAvanzados = document.getElementById("filtrosAvanzados");
const filtroBodega = document.getElementById("filtroBodega");
const filtroStockMin = document.getElementById("filtroStockMin");
const filtroStockMax = document.getElementById("filtroStockMax");
const filtroFechaDesde = document.getElementById("filtroFechaDesde");
const filtroFechaHasta = document.getElementById("filtroFechaHasta");
const filtroDiasBodega = document.getElementById("filtroDiasBodega");
const btnLimpiarFiltros = document.getElementById("btnLimpiarFiltros");
const cuerpoTabla = document.getElementById("cuerpoTabla");
const mensajeEstado = document.getElementById("mensajeEstado");
const contadorResultados = document.getElementById("contadorResultados");
const statProductos = document.getElementById("statProductos");
const statUnidades = document.getElementById("statUnidades");
const statValor = document.getElementById("statValor");
const btnDescargarExcel = document.getElementById("btnDescargarExcel");


let debounceTimer;
let bodegasCache = [];

// ================== CARGA INICIAL ==================
async function cargarDatosIniciales() {
  try {
    const bodegas = await cargarBodegas();
    bodegasCache = bodegas;
    filtroBodega.innerHTML = `<option value="">Todas las bodegas</option>` +
      bodegas.map(b => `<option value="${b.id}">${b.nombre}</option>`).join("");
  } catch (err) {
    console.error("Error cargando bodegas:", err);
    mostrarEstado("Error al cargar las bodegas. Recarga la página.");
  }
}

// ================== TOGGLE FILTROS ==================
btnMostrarFiltros.addEventListener("click", () => {
  filtrosAvanzados.classList.toggle("oculto");
  iconoFiltros.textContent = filtrosAvanzados.classList.contains("oculto") ? "▼" : "▲";
});

btnLimpiarFiltros.addEventListener("click", () => {
  filtroBodega.value = "";
  filtroStockMin.value = "";
  filtroStockMax.value = "";
  filtroFechaDesde.value = "";
  filtroFechaHasta.value = "";
  filtroDiasBodega.value = "";
  inpBuscar.value = "";
  buscar();
});

// ================== BÚSQUEDA CON DEBOUNCE ==================
inpBuscar.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  spinner.classList.remove("oculto");
  debounceTimer = setTimeout(buscar, 500); // Espera 500ms después de dejar de escribir
});

[filtroBodega, filtroStockMin, filtroStockMax, filtroFechaDesde, filtroFechaHasta, filtroDiasBodega]
  .forEach(el => el.addEventListener("change", buscar));

async function buscar() {
  const texto = inpBuscar.value.trim();
  const bodegaId = filtroBodega.value;
  const stockMin = filtroStockMin.value ? Number(filtroStockMin.value) : null;
  const stockMax = filtroStockMax.value ? Number(filtroStockMax.value) : null;
  const fechaDesde = filtroFechaDesde.value || null;
  const fechaHasta = filtroFechaHasta.value || null;
  const diasMax = filtroDiasBodega.value ? Number(filtroDiasBodega.value) : null;

  // Si no hay ningún filtro activo, mostrar mensaje inicial
  if (!texto && !bodegaId && stockMin === null && stockMax === null && !fechaDesde && !fechaHasta && diasMax === null) {
    mostrarEstado("Escribe algo en el buscador o ajusta los filtros para ver resultados.");
    cuerpoTabla.innerHTML = "";
    actualizarEstadisticas(0, 0, 0);
    contadorResultados.textContent = "";
    spinner.classList.add("oculto");
    return;
  }

  try {
    // Delegamos la petición a api.js
    const resultados = await buscarInventario({
      texto,
      bodegaId,
      stockMin,
      stockMax,
      fechaDesde,
      fechaHasta,
      diasMax
    });

    renderizarResultados(resultados);
  } catch (err) {
    console.error("Error buscando:", err);
    mostrarEstado(err.message || "Error al buscar. Intenta de nuevo.");
    cuerpoTabla.innerHTML = "";
    actualizarEstadisticas(0, 0, 0);
  } finally {
    spinner.classList.add("oculto");
  }
}


// ================== DESCARGA EXCEL ==================
btnDescargarExcel.addEventListener("click", async () => {
  const textoOriginal = btnDescargarExcel.textContent;
  btnDescargarExcel.disabled = true;
  btnDescargarExcel.textContent = "Generando Excel...";

  try {
    await descargarReporteStock();
  } catch (err) {
    console.error("Error descargando Excel:", err);
    alert(err.message || "No se pudo descargar el reporte.");
  } finally {
    btnDescargarExcel.disabled = false;
    btnDescargarExcel.textContent = textoOriginal;
  }
});

// ================== RENDERIZADO ==================
function renderizarResultados(resultados) {
  if (!resultados || resultados.length === 0) {
    mostrarEstado("No se encontraron resultados con los filtros aplicados.");
    cuerpoTabla.innerHTML = "";
    actualizarEstadisticas(0, 0, 0);
    contadorResultados.textContent = "";
    return;
  }

  mensajeEstado.classList.add("oculto");
  contadorResultados.textContent = `(${resultados.length})`;

  cuerpoTabla.innerHTML = resultados.map(item => `
    <tr>
      <td><strong>${item.producto_nombre}</strong></td>
      <td>${item.presentacion_nombre || 'N/A'}</td>
      <td>${item.bodega_nombre}</td>
      <td class="num">${item.stock}</td>
      <td class="num">$${Number(item.costo_unitario).toFixed(2)}</td>
      <td class="num">$${Number(item.valor_total).toFixed(2)}</td>
      <td class="num">${formatearDiasBodega(item.dias_bodega)}</td>
      <td>${formatearFecha(item.ultima_movimentacion)}</td>
    </tr>
  `).join("");

  // Calcular estadísticas
  const totalProductos = new Set(resultados.map(r => r.producto_nombre)).size;
  const totalUnidades = resultados.reduce((sum, r) => sum + Number(r.stock), 0);
  const totalValor = resultados.reduce((sum, r) => sum + Number(r.valor_total), 0);

  actualizarEstadisticas(totalProductos, totalUnidades, totalValor);
}

function formatearDiasBodega(dias) {
  if (dias <= 7) return `<span class="badge badge-verde">${dias} días</span>`;
  if (dias <= 30) return `<span class="badge badge-amarillo">${dias} días</span>`;
  return `<span class="badge badge-rojo">${dias} días</span>`;
}

function formatearFecha(fecha) {
  if (!fecha) return "N/A";
  const d = new Date(fecha);
  return d.toLocaleDateString('es-SV', { year: 'numeric', month: 'short', day: 'numeric' });
}

function mostrarEstado(mensaje) {
  mensajeEstado.textContent = mensaje;
  mensajeEstado.classList.remove("oculto");
}

function actualizarEstadisticas(productos, unidades, valor) {
  statProductos.textContent = productos;
  statUnidades.textContent = unidades;
  statValor.textContent = `$${Number(valor).toFixed(2)}`;
}

// ================== INICIALIZACIÓN ==================
document.addEventListener("DOMContentLoaded", cargarDatosIniciales);