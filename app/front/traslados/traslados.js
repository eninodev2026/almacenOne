// Usa las funciones de ..\api.js (cargarBodegas, cargarProductos,
// cargarPresentaciones y crearTraslado). Ahí vive la dirección de la API.

// ================== CÓMO SE MUESTRA CADA OPCIÓN ==================
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
const selectOrigen = document.getElementById("bodegaOrigen");
const selectDestino = document.getElementById("bodegaDestino");
const cuerpoLineas = document.getElementById("lineas");
const btnAgregar = document.getElementById("btnAgregar");
const btnGuardar = document.getElementById("btnGuardar");
const btnLimpiar = document.getElementById("btnLimpiar");
const caja = document.getElementById("mensaje");
const inpObservacion = document.getElementById("observacion");
// ================== UTILIDADES ==================
function mostrarMensaje(texto, tipo) {
  caja.textContent = texto;
  caja.className = tipo; // "ok" o "error"
}

function ocultarMensaje() {
  caja.textContent = "";
  caja.className = "";
}

// ================== CARGA INICIAL ==================
// Solo se cargan las bodegas. Productos y presentaciones se piden bajo demanda.
async function cargarDatos() {
  try {
    const bodegas = await cargarBodegas();

    const opcionesBodega = bodegas
      .map((b) => `<option value="${b.id}">${textoBodega(b)}</option>`)
      .join("");
    selectOrigen.innerHTML = opcionesBodega;
    selectDestino.innerHTML = opcionesBodega;

    // Para que de inicio no queden iguales, el destino arranca en la segunda bodega
    if (bodegas.length > 1) selectDestino.selectedIndex = 1;

    agregarLinea();
  } catch (err) {
    mostrarMensaje(err.message, "error");
  }
}

// ================== BUSCADOR DE PRODUCTOS (en el servidor) ==================
function textoProducto(p) {
  return (p.codigo ? p.codigo + " - " : "") + p.nombre;
}

// Convierte un <input> en buscador que consulta al servidor mientras se escribe.
// alElegir(producto) se llama al elegir uno (o con null si se borra la elección).
function crearBuscadorProductos(input, alElegir) {
  const lista = document.createElement("ul");
  lista.className = "ac-lista";
  input.parentElement.appendChild(lista);

  let coincidencias = [];
  let indice = -1;
  let temporizador = null;
  let controlador = null;

  function cerrar() {
    lista.style.display = "none";
    indice = -1;
  }

  function elegir(producto) {
    input.value = textoProducto(producto);
    cerrar();
    alElegir(producto);
  }

  function pintar(textoVacio) {
    lista.innerHTML = "";
    if (coincidencias.length === 0) {
      const vacio = document.createElement("li");
      vacio.className = "sin-resultados";
      vacio.textContent = textoVacio || "Sin resultados";
      lista.appendChild(vacio);
    }
    coincidencias.forEach((producto, i) => {
      const li = document.createElement("li");
      li.textContent = textoProducto(producto);
      if (i === indice) li.className = "activa";
      // mousedown (y no click) para que funcione antes de que el input pierda el foco
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        elegir(producto);
      });
      lista.appendChild(li);
    });
    lista.style.display = "block";
  }

  async function buscar() {
    const texto = input.value.trim();
    if (texto.length < 2) {
      cerrar();
      return;
    }

    if (controlador) controlador.abort(); // cancela la búsqueda anterior
    controlador = new AbortController();

    try {
      coincidencias = await cargarProductos({
        texto: texto,
        limite: 8,
        signal: controlador.signal,
      });
      indice = -1;
      pintar();
    } catch (err) {
      if (err.name === "AbortError") return;
      coincidencias = [];
      pintar("No se pudo buscar");
    }
  }

  input.addEventListener("input", () => {
    alElegir(null); // si escribe de nuevo, la elección anterior ya no vale
    clearTimeout(temporizador);
    temporizador = setTimeout(buscar, 300); // espera a que deje de escribir
  });
  input.addEventListener("focus", buscar);
  input.addEventListener("blur", cerrar);

  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      indice = Math.min(indice + 1, coincidencias.length - 1);
      pintar();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      indice = Math.max(indice - 1, 0);
      pintar();
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (indice >= 0) elegir(coincidencias[indice]);
      else if (coincidencias.length === 1) elegir(coincidencias[0]);
    } else if (e.key === "Escape") {
      cerrar();
    }
  });
}

// ================== LÍNEAS DE DETALLE ==================
function agregarLinea() {
  const fila = document.createElement("tr");
  fila.innerHTML = `
    <td class="ac-contenedor">
      <input type="text" class="inp-producto" placeholder="Escribe 2 letras para buscar..." autocomplete="off">
    </td>
    <td><select class="sel-presentacion"></select></td>
    <td class="col-cantidad">
      <input type="number" class="inp-cantidad" min="0" step="any" placeholder="0">
    </td>
    <td class="col-equivale"></td>
    <td class="col-quitar">
      <button type="button" class="btn-quitar" title="Quitar">✕</button>
    </td>
  `;

  const inpProducto = fila.querySelector(".inp-producto");
  const selPresentacion = fila.querySelector(".sel-presentacion");
  const inpCantidad = fila.querySelector(".inp-cantidad");
  const equivale = fila.querySelector(".col-equivale");

  let presentacionesDelProducto = []; // solo las del producto elegido en esta fila
  let version = 0; // evita que una respuesta lenta pise a una más nueva

  function actualizarEquivale() {
    const p = presentacionesDelProducto.find((x) => String(x.id) === selPresentacion.value);
    const cantidad = Number(inpCantidad.value);
    if (!p || !(cantidad > 0)) {
      equivale.textContent = "";
      return;
    }
    equivale.textContent = `${cantidad} × ${nombrePresentacion(p)} = ${cantidad * Number(p.factor)} unidades`;
  }

  async function alElegirProducto(producto) {
    const miVersion = ++version;
    presentacionesDelProducto = [];
    selPresentacion.innerHTML = "";
    actualizarEquivale();
    if (!producto) return;

    selPresentacion.innerHTML = '<option value="">Cargando...</option>';
    try {
      const lista = await cargarPresentaciones(producto.id);
      if (miVersion !== version) return;
      presentacionesDelProducto = lista;
      selPresentacion.innerHTML = lista.length
        ? lista.map((p) => `<option value="${p.id}">${textoPresentacion(p)}</option>`).join("")
        : '<option value="">Este producto no tiene presentaciones</option>';
    } catch (err) {
      if (miVersion !== version) return;
      selPresentacion.innerHTML = '<option value="">No se pudieron cargar</option>';
      mostrarMensaje(err.message, "error");
    }
    actualizarEquivale();
  }

  crearBuscadorProductos(inpProducto, alElegirProducto);
  selPresentacion.addEventListener("change", actualizarEquivale);
  inpCantidad.addEventListener("input", actualizarEquivale);

  fila.querySelector(".btn-quitar").addEventListener("click", () => {
    fila.remove();
    if (cuerpoLineas.children.length === 0) agregarLinea();
  });

  cuerpoLineas.appendChild(fila);
}

function leerDetalles() {
  const detalles = [];
  for (const fila of cuerpoLineas.children) {
    const presentacionId = Number(fila.querySelector(".sel-presentacion").value);
    const cantidad = Number(fila.querySelector(".inp-cantidad").value);

    if (!presentacionId) throw new Error("Elige producto y presentación en todas las líneas");
    if (!(cantidad > 0)) throw new Error("La cantidad debe ser mayor a 0 en todas las líneas");

    detalles.push({ presentacion_id: presentacionId, cantidad: cantidad });
  }
  return detalles;
}

// ================== GUARDAR ==================
async function guardarTraslado() {
  ocultarMensaje();

  let cuerpo;
  try {
    const origenId = Number(selectOrigen.value);
    const destinoId = Number(selectDestino.value);
    if (!origenId) throw new Error("Elige la bodega de origen");
    if (!destinoId) throw new Error("Elige la bodega de destino");
    if (origenId === destinoId) {
      throw new Error("La bodega de origen y la de destino no pueden ser la misma");
    }
    cuerpo = {
      bodega_origen_id: origenId,
      bodega_destino_id: destinoId,
      observacion: inpObservacion.value.trim() || null,
      detalles: leerDetalles(),
    };
  } catch (err) {
    mostrarMensaje(err.message, "error");
    return;
  }

  btnGuardar.disabled = true;
  btnGuardar.textContent = "Guardando...";

  try {
    const datos = await crearTraslado(cuerpo);

      mostrarMensaje(
      `Traslado #${datos.movimiento_id} ${datos.estado}: ` +
        `${datos.productos_afectados} producto(s) salieron de la bodega de origen ` +
        `y quedan pendientes de recepción en el destino.`,
      "ok"
    );
    limpiarFormulario(false);

  try {
      await descargarComprobanteTraslado(datos.movimiento_id);
    } catch (errPdf) {
      mostrarMensaje(
        `Traslado #${datos.movimiento_id} registrado, pero no se pudo descargar el comprobante: ${errPdf.message}`,
        "error"
      );
  }


  } catch (err) {
    // TypeError = el navegador no pudo llegar al servidor
    mostrarMensaje(
      err instanceof TypeError ? "No se pudo conectar con el servidor" : err.message,
      "error"
    );
  } finally {
    btnGuardar.disabled = false;
    btnGuardar.textContent = "Registrar traslado";
  }
}

function limpiarFormulario(borrarMensaje = true) {
  cuerpoLineas.innerHTML = "";
  inpObservacion.value = "";
  agregarLinea();
  if (borrarMensaje) ocultarMensaje();
}

// ================== EVENTOS ==================
btnAgregar.addEventListener("click", agregarLinea);
btnGuardar.addEventListener("click", guardarTraslado);
btnLimpiar.addEventListener("click", () => limpiarFormulario(true));
document.addEventListener("DOMContentLoaded", cargarDatos);