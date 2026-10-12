// Usa las funciones de ..\api.js (cargarBodegas, cargarProductos,
// cargarPresentaciones y crearSalida). Ahí vive la dirección de la API.

// ================== CÓMO SE MUESTRA CADA OPCIÓN ==================
function textoBodega(b) {
  return b.nombre;
}

function nombrePresentacion(p) {
  return p.unidad_nombre || `Presentación #${p.id}`;
}

function textoPresentacion(p) {
  // factor 1 = se vende suelto (granel); factor mayor = trae varias unidades (caja)
  const factor = Number(p.factor);
  const nombre = nombrePresentacion(p);
  return factor === 1
    ? `${nombre} (granel, 1 unidad)`
    : `${nombre} (trae ${factor} unidades)`;
}

// ================== ELEMENTOS ==================
const selectBodega = document.getElementById("bodega");
const cuerpoLineas = document.getElementById("lineas");
const btnAgregar = document.getElementById("btnAgregar");
const btnGuardar = document.getElementById("btnGuardar");
const btnLimpiar = document.getElementById("btnLimpiar");
const caja = document.getElementById("mensaje");

let presentaciones = [];
let productos = [];

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
async function cargarDatos() {
  try {
    const [bodegas, pres, prods] = await Promise.all([
      cargarBodegas(),
      cargarPresentaciones(),
      cargarProductos(),
    ]);
    presentaciones = pres;
    productos = prods;

    selectBodega.innerHTML = bodegas
      .map((b) => `<option value="${b.id}">${textoBodega(b)}</option>`)
      .join("");

    agregarLinea();
  } catch (err) {
    mostrarMensaje(err.message, "error");
  }
}


// ================== AUTOCOMPLETADO ==================
// Convierte un <input> en buscador. opciones = lista de { id, texto }.
// alElegir(id) se llama al elegir una opción (o con null si se borra la elección).
function crearAutocompletado(input, opciones, alElegir) {
  const lista = document.createElement("ul");
  lista.className = "ac-lista";
  input.parentElement.appendChild(lista);

  let coincidencias = [];
  let indice = -1;

  function normalizar(texto) {
    return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function cerrar() {
    lista.style.display = "none";
    indice = -1;
  }

  function elegir(opcion) {
    input.value = opcion.texto;
    cerrar();
    alElegir(opcion.id);
  }

  function pintar() {
    lista.innerHTML = "";
    if (coincidencias.length === 0) {
      const vacio = document.createElement("li");
      vacio.className = "sin-resultados";
      vacio.textContent = "Sin resultados";
      lista.appendChild(vacio);
    }
    coincidencias.forEach((opcion, i) => {
      const li = document.createElement("li");
      li.textContent = opcion.texto;
      if (i === indice) li.className = "activa";
      // mousedown (y no click) para que funcione antes de que el input pierda el foco
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        elegir(opcion);
      });
      lista.appendChild(li);
    });
    lista.style.display = "block";
  }

  function buscar() {
    const palabras = normalizar(input.value).split(" ").filter(Boolean);
    coincidencias = opciones
      .filter((op) => palabras.every((pal) => normalizar(op.texto).includes(pal)))
      .slice(0, 8);
    indice = -1;
    pintar();
  }

  input.addEventListener("input", () => {
    alElegir(null); // si escribe de nuevo, la elección anterior ya no vale
    buscar();
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

// Lista de productos que se pueden buscar (los que tienen al menos una presentación)
function productosParaBuscar() {
  const ids = [...new Set(presentaciones.map((p) => p.producto_id))];
  return ids.map((id) => {
    const prod = productos.find((x) => x.id === id);
    const p = presentaciones.find((x) => x.producto_id === id);
    const nombre = prod?.nombre || p.producto_nombre || `Producto #${id}`;
    const codigo = prod?.codigo ? `${prod.codigo} - ` : "";
    return { id: id, texto: codigo + nombre };
  });
}



// ================== LÍNEAS DE DETALLE ==================
// Productos que tienen al menos una presentación
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
    <td class="ac-contenedor">
      <input type="text" class="inp-producto" placeholder="Buscar producto..." autocomplete="off">
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
  let productoId = "";

  function llenarPresentaciones() {
    const lista = presentaciones.filter(
      (p) => String(p.producto_id) === String(productoId)
    );
    selPresentacion.innerHTML = lista
      .map((p) => `<option value="${p.id}">${textoPresentacion(p)}</option>`)
      .join("");
    actualizarEquivale();
  }

  function actualizarEquivale() {
    const p = presentaciones.find((x) => String(x.id) === selPresentacion.value);
    const cantidad = Number(inpCantidad.value);
    if (!p || !(cantidad > 0)) {
      equivale.textContent = "";
      return;
    }
    equivale.textContent = `${cantidad} × ${nombrePresentacion(p)} = ${cantidad * Number(p.factor)} unidades`;
  }

  crearAutocompletado(inpProducto, productosParaBuscar(), (id) => {
    productoId = id || "";
    llenarPresentaciones();
  });
  selPresentacion.addEventListener("change", actualizarEquivale);
  inpCantidad.addEventListener("input", actualizarEquivale);

  fila.querySelector(".btn-quitar").addEventListener("click", () => {
    fila.remove();
    if (cuerpoLineas.children.length === 0) agregarLinea();
  });

  cuerpoLineas.appendChild(fila);
  llenarPresentaciones();
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
async function guardarSalida() {
  ocultarMensaje();

  let cuerpo;
  try {
    const bodegaId = Number(selectBodega.value);
    if (!bodegaId) throw new Error("Elige una bodega");
    cuerpo = { bodega_id: bodegaId, detalles: leerDetalles() };
  } catch (err) {
    mostrarMensaje(err.message, "error");
    return;
  }

  btnGuardar.disabled = true;
  btnGuardar.textContent = "Guardando...";

  try {
    const datos = await crearSalida(cuerpo);

    mostrarMensaje(
      `Salida registrada (movimiento #${datos.movimiento_id}, ` +
        `${datos.productos_afectados} producto(s) afectado(s))`,
      "ok"
    );
    limpiarFormulario(false);

    try {
      await descargarHojaSalida(datos.movimiento_id);
    } catch (errPdf) {
      mostrarMensaje(
        `Salida registrada (movimiento #${datos.movimiento_id}), ` +
          `pero no se pudo descargar la hoja: ${errPdf.message}`,
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
    btnGuardar.textContent = "Registrar salida";
  }
}

function limpiarFormulario(borrarMensaje = true) {
  cuerpoLineas.innerHTML = "";
  agregarLinea();
  if (borrarMensaje) ocultarMensaje();
}

// ================== EVENTOS ==================
btnAgregar.addEventListener("click", agregarLinea);
btnGuardar.addEventListener("click", guardarSalida);
btnLimpiar.addEventListener("click", () => limpiarFormulario(true));
document.addEventListener("DOMContentLoaded", cargarDatos);

