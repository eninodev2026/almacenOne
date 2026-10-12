// Usa las funciones de ..\api.js (cargarProveedores, cargarBodegas, cargarProductos,
// cargarPresentaciones y crearCompra). Ahí vive la dirección de la API.

const TASA_IVA = 0.13; // igual que en el backend

// ================== CÓMO SE MUESTRA CADA OPCIÓN ==================
function textoProveedor(p) {
  return p.nombre;
}

function textoBodega(b) {
  return b.nombre;
}

function nombrePresentacion(p) {
  return p.unidad_nombre || `Presentación #${p.id}`;
}

function textoPresentacion(p) {
  const factor = Number(p.factor);
  const nombre = nombrePresentacion(p);
  return factor === 1
    ? `${nombre} (granel, 1 unidad)`
    : `${nombre} (trae ${factor} unidades)`;
}

// ================== ELEMENTOS ==================
const selProveedor = document.getElementById("proveedor");
const selBodega = document.getElementById("bodega");
const inpFactura = document.getElementById("numeroFactura");
const inpCondicion = document.getElementById("condicionPago");
const inpFechaEmision = document.getElementById("fechaEmision");
const inpFechaCompra = document.getElementById("fechaCompra");
const inpObservacion = document.getElementById("observacion");
const cuerpoLineas = document.getElementById("lineas");
const btnAgregar = document.getElementById("btnAgregar");
const btnGuardar = document.getElementById("btnGuardar");
const btnLimpiar = document.getElementById("btnLimpiar");
const caja = document.getElementById("mensaje");
const totSubtotal = document.getElementById("totSubtotal");
const totDescuento = document.getElementById("totDescuento");
const totIva = document.getElementById("totIva");
const totTotal = document.getElementById("totTotal");

// Elementos nuevos para JSON
const inpArchivoJson = document.getElementById("archivoJson");
const btnSeleccionarJson = document.getElementById("btnSeleccionarJson");
const btnImportarJson = document.getElementById("btnImportarJson");
const nombreArchivoJson = document.getElementById("nombreArchivoJson");

let presentaciones = [];
let productos = [];
let proveedoresCache = []; // Para buscar por NIT al importar

// ================== UTILIDADES ==================
function mostrarMensaje(texto, tipo) {
  caja.textContent = texto;
  caja.className = tipo; // "ok" o "error"
}

function ocultarMensaje() {
  caja.textContent = "";
  caja.className = "";
}

function dinero(numero) {
  return "$" + Number(numero).toFixed(2);
}

function dinero4(numero) {
  return "$" + Number(numero).toFixed(4);
}

// Fecha de hoy como AAAA-MM-DD, con la hora local (no la de UTC)
function fechaHoy() {
  const d = new Date();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

// ================== CARGA INICIAL ==================
async function cargarDatos() {
  inpFechaEmision.value = fechaHoy();
  inpFechaCompra.value = fechaHoy();

  try {
    const [proveedores, bodegas, pres, prods] = await Promise.all([
      cargarProveedores(),
      cargarBodegas(),
      cargarPresentaciones(),
      cargarProductos(),
    ]);
    proveedoresCache = proveedores;
    presentaciones = pres;
    productos = prods;

    selProveedor.innerHTML = `<option value="">-- Seleccione --</option>` + 
      proveedores.map((p) => `<option value="${p.id}">${textoProveedor(p)}</option>`).join("");
    selBodega.innerHTML = `<option value="">-- Seleccione --</option>` + 
      bodegas.map((b) => `<option value="${b.id}">${textoBodega(b)}</option>`).join("");

    agregarLinea();
  } catch (err) {
    mostrarMensaje(err.message, "error");
  }
}

// ================== LÓGICA DE IMPORTACIÓN JSON (DTE) ==================
btnSeleccionarJson.addEventListener("click", () => inpArchivoJson.click());

inpArchivoJson.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) {
    nombreArchivoJson.textContent = file.name;
    btnImportarJson.disabled = false;
  } else {
    nombreArchivoJson.textContent = "Ningún archivo seleccionado";
    btnImportarJson.disabled = true;
  }
});

btnImportarJson.addEventListener("click", () => {
  const file = inpArchivoJson.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(event) {
    try {
      const dte = JSON.parse(event.target.result);
      procesarDTE(dte);
    } catch (err) {
      mostrarMensaje("El archivo no es un JSON válido o está corrupto.", "error");
    }
  };
  reader.readAsText(file);
});

function procesarDTE(dte) {
  try {
    // 1. Validar estructura básica
    if (!dte.identificacion || !dte.emisor || !dte.cuerpoDocumento) {
      throw new Error("El JSON no tiene la estructura esperada de un DTE (faltan identificacion, emisor o cuerpoDocumento).");
    }

    // 2. Llenar cabecera
    inpFactura.value = dte.identificacion.numeroControl || "";
    inpFechaEmision.value = dte.identificacion.fecEmi || fechaHoy();
    inpFechaCompra.value = fechaHoy();
    inpObservacion.value = `DTE Importado. Código: ${dte.identificacion.codigoGeneracion || 'N/A'}`;
    
    const condicion = dte.resumen?.condicionOperacion === 1 ? "Contado" : "Crédito";
    inpCondicion.value = condicion;

    // 3. Intentar buscar proveedor por NIT
    const nitEmisor = dte.emisor.nit;
    const proveedorEncontrado = proveedoresCache.find(p => p.nit === nitEmisor);
    if (proveedorEncontrado) {
      selProveedor.value = proveedorEncontrado.id;
    } else {
      mostrarMensaje(`Advertencia: Proveedor con NIT ${nitEmisor} no está registrado. Selecciónelo manualmente o regístrelo primero.`, "error");
      selProveedor.value = "";
    }

    // 4. Limpiar líneas actuales y cargar las del DTE
    cuerpoLineas.innerHTML = "";
    let productosNoEncontrados = [];

    for (const item of dte.cuerpoDocumento) {
      agregarLineaDesdeDTE(item, productosNoEncontrados);
    }

    recalcularTotales();

    if (productosNoEncontrados.length > 0) {
      mostrarMensaje(
        `DTE importado. Atención: No se pudieron auto-seleccionar estos productos: ${productosNoEncontrados.join(", ")}. Por favor, selecciónelos manualmente en la tabla.`, 
        "error"
      );
    } else {
      mostrarMensaje("DTE importado exitosamente. Verifique los datos y guarde.", "ok");
    }

    // Resetear input file
    inpArchivoJson.value = "";
    nombreArchivoJson.textContent = "Ningún archivo seleccionado";
    btnImportarJson.disabled = true;

  } catch (err) {
    mostrarMensaje("Error al procesar el DTE: " + err.message, "error");
  }
}

function agregarLineaDesdeDTE(item, listaFallos) {
  const fila = document.createElement("tr");
  fila.innerHTML = `
    <td><select class="sel-producto"><option value="">-- Buscar --</option>${opcionesProductos()}</select></td>
    <td><select class="sel-presentacion"></select></td>
    <td class="col-cantidad"><input type="number" class="inp-cantidad" min="0" step="any" placeholder="0"></td>
    <td class="col-precio"><input type="number" class="inp-precio" min="0" step="any" placeholder="0.00"></td>
    <td class="col-descuento"><input type="number" class="inp-descuento" min="0" step="any" value="0"></td>
    <td class="col-entra"></td>
    <td class="col-total num"></td>
    <td class="col-quitar"><button type="button" class="btn-quitar" title="Quitar">✕</button></td>
  `;

  cuerpoLineas.appendChild(fila);

  const selProducto = fila.querySelector(".sel-producto");
  const selPresentacion = fila.querySelector(".sel-presentacion");
  const inpCantidad = fila.querySelector(".inp-cantidad");
  const inpPrecio = fila.querySelector(".inp-precio");
  const inpDescuento = fila.querySelector(".inp-descuento");

  // Lógica de emparejamiento inteligente
  const descLower = item.descripcion.toLowerCase();
  const prodEncontrado = productos.find(p => 
    p.nombre.toLowerCase().includes(descLower) || descLower.includes(p.nombre.toLowerCase())
  );

  if (prodEncontrado) {
    selProducto.value = prodEncontrado.id;
    // Disparar evento para llenar presentaciones
    selProducto.dispatchEvent(new Event('change'));
    
    // Intentar seleccionar la primera presentación disponible de ese producto
    setTimeout(() => {
      const presDelProducto = presentaciones.filter(p => String(p.producto_id) === String(prodEncontrado.id));
      if (presDelProducto.length > 0) {
        selPresentacion.value = presDelProducto[0].id;
      }
    }, 50);
  } else {
    listaFallos.push(`"${item.descripcion}"`);
  }

  // Llenar datos numéricos
  inpCantidad.value = item.cantidad;
  inpPrecio.value = item.precioUni;
  inpDescuento.value = item.montoDescu || 0;

  // Configurar eventos de la fila (mismos que en agregarLinea normal)
  function llenarPresentaciones() {
    const lista = presentaciones.filter(p => String(p.producto_id) === selProducto.value);
    selPresentacion.innerHTML = lista
      .map((p) => `<option value="${p.id}">${textoPresentacion(p)}</option>`)
      .join("");
    actualizarFila(fila);
    recalcularTotales();
  }

  selProducto.addEventListener("change", llenarPresentaciones);
  fila.addEventListener("input", () => { actualizarFila(fila); recalcularTotales(); });
  fila.addEventListener("change", () => { actualizarFila(fila); recalcularTotales(); });

  fila.querySelector(".btn-quitar").addEventListener("click", () => {
    fila.remove();
    if (cuerpoLineas.children.length === 0) agregarLinea();
    recalcularTotales();
  });

  // Inicializar
  llenarPresentaciones();
}


// ================== LÍNEAS DE DETALLE (MANUAL) ==================
function opcionesProductos() {
  const ids = [...new Set(presentaciones.map((p) => p.producto_id))];
  return ids
    .map((id) => {
      const prod = productos.find((x) => x.id === id);
      const p = presentaciones.find((x) => x.producto_id === id);
      const nombre = prod?.nombre || p.producto_nombre || `Producto #${id}`;
      return `<option value="${id}">${nombre}</option>`;
    })
    .join("");
}

function agregarLinea() {
  const fila = document.createElement("tr");
  fila.innerHTML = `
    <td><select class="sel-producto"><option value="">-- Seleccione --</option>${opcionesProductos()}</select></td>
    <td><select class="sel-presentacion"></select></td>
    <td class="col-cantidad"><input type="number" class="inp-cantidad" min="0" step="any" placeholder="0"></td>
    <td class="col-precio"><input type="number" class="inp-precio" min="0" step="any" placeholder="0.00"></td>
    <td class="col-descuento"><input type="number" class="inp-descuento" min="0" step="any" value="0"></td>
    <td class="col-entra"></td>
    <td class="col-total num"></td>
    <td class="col-quitar"><button type="button" class="btn-quitar" title="Quitar">✕</button></td>
  `;

  const selProducto = fila.querySelector(".sel-producto");
  const selPresentacion = fila.querySelector(".sel-presentacion");

  function llenarPresentaciones() {
    const lista = presentaciones.filter(
      (p) => String(p.producto_id) === selProducto.value
    );
    selPresentacion.innerHTML = lista
      .map((p) => `<option value="${p.id}">${textoPresentacion(p)}</option>`)
      .join("");
    actualizarFila(fila);
    recalcularTotales();
  }

  selProducto.addEventListener("change", llenarPresentaciones);
  fila.addEventListener("input", () => { actualizarFila(fila); recalcularTotales(); });
  fila.addEventListener("change", () => { actualizarFila(fila); recalcularTotales(); });

  fila.querySelector(".btn-quitar").addEventListener("click", () => {
    fila.remove();
    if (cuerpoLineas.children.length === 0) agregarLinea();
    recalcularTotales();
  });

  cuerpoLineas.appendChild(fila);
  llenarPresentaciones();
}

function datosDeFila(fila) {
  const presentacion = presentaciones.find(
    (p) => String(p.id) === fila.querySelector(".sel-presentacion").value
  );
  return {
    presentacion: presentacion,
    cantidad: Number(fila.querySelector(".inp-cantidad").value),
    precioVacio: fila.querySelector(".inp-precio").value === "",
    precio: Number(fila.querySelector(".inp-precio").value),
    descuento: Number(fila.querySelector(".inp-descuento").value),
  };
}

function actualizarFila(fila) {
  const entra = fila.querySelector(".col-entra");
  const total = fila.querySelector(".col-total");
  const d = datosDeFila(fila);

  if (!d.presentacion || !(d.cantidad > 0)) {
    entra.textContent = "";
    total.textContent = "";
    return;
  }

  const factor = Number(d.presentacion.factor);
  const unidadesQueEntran = Number((d.cantidad * factor).toFixed(4));
  let texto = `${unidadesQueEntran} unidades`;
  if (!d.precioVacio && d.precio > 0) {
    texto += ` · costo ${dinero4(d.precio / factor)} c/u`;
  }
  entra.textContent = texto;
  total.textContent = dinero(d.cantidad * d.precio - d.descuento);
}

function recalcularTotales() {
  let subtotal = 0;
  let descuento = 0;

  for (const fila of cuerpoLineas.children) {
    const d = datosDeFila(fila);
    if (d.presentacion && d.cantidad > 0) {
      subtotal += d.cantidad * d.precio;
      descuento += d.descuento;
    }
  }

  const iva = (subtotal - descuento) * TASA_IVA;
  totSubtotal.textContent = dinero(subtotal);
  totDescuento.textContent = dinero(descuento);
  totIva.textContent = dinero(iva);
  totTotal.textContent = dinero(subtotal - descuento + iva);
}

function leerDetalles() {
  const detalles = [];
  for (const fila of cuerpoLineas.children) {
    const d = datosDeFila(fila);

    if (!d.presentacion) throw new Error("Elige producto y presentación en todas las líneas");
    if (!(d.cantidad > 0)) throw new Error("La cantidad debe ser mayor a 0 en todas las líneas");
    if (d.precioVacio || d.precio < 0) throw new Error("Escribe el precio unitario en todas las líneas");
    if (d.descuento < 0) throw new Error("El descuento no puede ser negativo");
    if (d.descuento > d.cantidad * d.precio) {
      throw new Error("El descuento no puede ser mayor al total de la línea");
    }

    detalles.push({
      presentacion_id: d.presentacion.id,
      cantidad: d.cantidad,
      precio_unitario: d.precio,
      descuento: d.descuento,
    });
  }
  return detalles;
}

// ================== GUARDAR ==================
function leerFormulario() {
  const proveedorId = Number(selProveedor.value);
  const bodegaId = Number(selBodega.value);
  const numeroFactura = inpFactura.value.trim();
  const condicion = inpCondicion.value.trim();

  if (!proveedorId) throw new Error("Elige un proveedor");
  if (!bodegaId) throw new Error("Elige una bodega");
  if (!numeroFactura) throw new Error("Escribe el número de factura");
  if (!inpFechaEmision.value) throw new Error("Elige la fecha de emisión");
  if (!inpFechaCompra.value) throw new Error("Elige la fecha de compra");
  if (!condicion) throw new Error("Escribe la condición de pago");

  return {
    proveedor_id: proveedorId,
    bodega_id: bodegaId,
    numero_factura: numeroFactura,
    fecha_emision: inpFechaEmision.value,
    fecha_compra: inpFechaCompra.value,
    condicion_pago: condicion,
    observacion: inpObservacion.value.trim() || null,
    detalles: leerDetalles(),
  };
}

async function guardarCompra() {
  ocultarMensaje();

  let cuerpo;
  try {
    cuerpo = leerFormulario();
  } catch (err) {
    mostrarMensaje(err.message, "error");
    return;
  }

  btnGuardar.disabled = true;
  btnGuardar.textContent = "Guardando...";

  try {
    const datos = await crearCompra(cuerpo);

    mostrarMensaje(
      `Compra registrada (factura ${datos.numero_factura}, total ${dinero(Number(datos.total))}). ` +
        `La mercadería ya entró al inventario.`,
      "ok"
    );
    limpiarFormulario(false);
  } catch (err) {
    mostrarMensaje(
      err instanceof TypeError ? "No se pudo conectar con el servidor" : err.message,
      "error"
    );
  } finally {
    btnGuardar.disabled = false;
    btnGuardar.textContent = "Registrar compra";
  }
}

function limpiarFormulario(borrarMensaje = true) {
  inpFactura.value = "";
  inpObservacion.value = "";
  inpFechaEmision.value = fechaHoy();
  inpFechaCompra.value = fechaHoy();
  inpCondicion.value = "Contado";
  selProveedor.value = "";
  selBodega.value = "";
  cuerpoLineas.innerHTML = "";
  agregarLinea();
  recalcularTotales();
  if (borrarMensaje) ocultarMensaje();
  
  // Resetear estado del JSON
  inpArchivoJson.value = "";
  nombreArchivoJson.textContent = "Ningún archivo seleccionado";
  btnImportarJson.disabled = true;
}

// ================== EVENTOS ==================
btnAgregar.addEventListener("click", agregarLinea);
btnGuardar.addEventListener("click", guardarCompra);
btnLimpiar.addEventListener("click", () => limpiarFormulario(true));
document.addEventListener("DOMContentLoaded", cargarDatos);