// Pantalla "Crear presentaciones".
// Usa las funciones de ..\api.js (cargarProductos, cargarUnidades,
// cargarPresentaciones y crearPresentacion). Ahí vive la dirección de la API.
//
// Esta pantalla tiene DOS buscadores de producto con autocompletado:
//   1) El del formulario: elige a qué producto se le crea la presentación.
//   2) El del filtro de la lista: muestra solo las presentaciones de un producto.
// Los dos se construyen con la misma función: crearAutocompletar().

// ================== ELEMENTOS ==================
// OJO: "selProducto" y "filtroProducto" son campos OCULTOS (type="hidden").
// Guardan solo el id del producto elegido; el texto visible está en
// "inpBuscarProducto" y "inpFiltroBuscar".
const selProducto = document.getElementById("producto");
const inpBuscarProducto = document.getElementById("productoBuscar");
const listaProductos = document.getElementById("listaProductos");

const filtroProducto = document.getElementById("filtroProducto");
const inpFiltroBuscar = document.getElementById("filtroBuscar");
const listaFiltro = document.getElementById("listaFiltro");

const selUnidad = document.getElementById("unidad");
const inpFactor = document.getElementById("factor");
const inpPrecio = document.getElementById("precio");
const btnGuardar = document.getElementById("btnGuardar");
const btnLimpiar = document.getElementById("btnLimpiar");
const caja = document.getElementById("mensaje");
const tabla = document.getElementById("tablaPresentaciones");
const sinDatos = document.getElementById("sinDatos");
const pistaFactor = document.getElementById("pistaFactor");

let unidades = [];

// Producto completo (con su unidad_base_id) elegido en el buscador del
// formulario. Es null mientras no haya ninguno elegido.
let productoElegido = null;

// ================== UTILIDADES ==================
function mostrarMensaje(texto, tipo) {
  caja.textContent = texto;
  caja.className = tipo; // "ok" o "error"
}

function ocultarMensaje() {
  caja.textContent = "";
  caja.className = "";
}

function opciones(lista) {
  return lista
    .map((x) => {
      const opt = document.createElement("option");
      opt.value = x.id;
      opt.textContent = x.nombre;
      return opt.outerHTML;
    })
    .join("");
}

function celda(texto, clase) {
  const td = document.createElement("td");
  td.textContent = texto;
  if (clase) td.className = clase;
  return td;
}

// ================== AUTOCOMPLETADO DE PRODUCTOS ==================
// Convierte un campo de texto en un buscador de productos.
// Cómo funciona:
//   - Cuando el usuario escribe, espera 250 ms sin teclear y recién entonces
//     le pide al servidor los productos que coinciden (máximo 10).
//   - Si el usuario sigue escribiendo, cancela la búsqueda anterior.
//   - Al elegir un producto, guarda su id en el campo oculto y avisa con onCambio.
//
// Parámetros:
//   input    -> campo de texto donde se escribe
//   oculto   -> campo oculto donde se guarda el id elegido
//   lista    -> <ul> donde se muestran las sugerencias
//   onCambio -> función que se ejecuta cuando cambia el producto elegido.
//               Recibe el producto completo, o null si se borró la selección.
function crearAutocompletar({ input, oculto, lista, onCambio }) {
  let resultados = []; // productos que se están mostrando
  let indiceActivo = -1; // posición resaltada con las flechas
  let temporizador = null; // espera de 250 ms antes de buscar
  let controlador = null; // permite cancelar la búsqueda en curso

  // Dibuja la lista. Si recibe "mensaje", muestra solo ese texto
  // (por ejemplo "Buscando..."); si no, dibuja los resultados.
  function dibujar(mensaje) {
    lista.innerHTML = "";

    if (mensaje) {
      const li = document.createElement("li");
      li.className = "vacio";
      li.textContent = mensaje;
      lista.appendChild(li);
    } else {
      resultados.forEach((p, i) => {
        const li = document.createElement("li");
        li.textContent = p.nombre;
        if (i === indiceActivo) li.classList.add("activo");
        // Se usa "mousedown" y no "click" para que el producto se elija
        // antes de que el campo de texto pierda el foco.
        li.addEventListener("mousedown", (e) => {
          e.preventDefault();
          elegir(p);
        });
        lista.appendChild(li);
      });
    }

    lista.hidden = false;

    // Mantiene visible el elemento resaltado cuando se navega con flechas
    const activo = lista.querySelector(".activo");
    if (activo) activo.scrollIntoView({ block: "nearest" });
  }

  // Pide al servidor los productos que coinciden con el texto.
  // Si el texto está vacío NO busca nada: la lista solo existe mientras se escribe.
  async function buscar(texto) {
    if (!texto) {
      cerrar();
      return;
    }

    if (controlador) controlador.abort(); // cancela la búsqueda anterior
    controlador = new AbortController();

    resultados = [];
    indiceActivo = -1;
    dibujar("Buscando...");

    try {
      const datos = await cargarProductos({
        texto: texto,
        signal: controlador.signal,
      });
      resultados = datos;
      indiceActivo = datos.length ? 0 : -1;
      dibujar(datos.length ? null : "Sin resultados");
    } catch (err) {
      if (err.name === "AbortError") return; // se canceló a propósito, no es error
      dibujar("No se pudo buscar");
    }
  }

  // Oculta la lista y cancela cualquier búsqueda pendiente
  function cerrar() {
    lista.hidden = true;
    clearTimeout(temporizador);
    if (controlador) controlador.abort();
  }

  // Guarda el producto elegido y avisa a quien use el buscador
  function elegir(p) {
    oculto.value = p.id;
    input.value = p.nombre;
    cerrar();
    onCambio(p);
  }

  // El usuario escribe: la selección anterior ya no vale y se busca de nuevo.
  // Si borró todo el texto, la lista se cierra y no se busca nada.
  input.addEventListener("input", () => {
    if (oculto.value) {
      oculto.value = "";
      onCambio(null);
    }
    clearTimeout(temporizador);

    const texto = input.value.trim();
    if (!texto) {
      cerrar();
      return;
    }
    temporizador = setTimeout(() => buscar(texto), 250);
  });

  // Al entrar al campo solo se selecciona el texto. NO se abre ninguna lista.
  input.addEventListener("focus", () => {
    input.select();
  });

  // Teclado: flechas para moverse, Enter para elegir, Escape para cerrar
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (lista.hidden) {
        buscar(input.value.trim()); // si no hay texto, no hace nada
        return;
      }
      if (resultados.length === 0) return;
      if (e.key === "ArrowDown") {
        indiceActivo = Math.min(indiceActivo + 1, resultados.length - 1);
      } else {
        indiceActivo = Math.max(indiceActivo - 1, 0);
      }
      dibujar(null);
    } else if (e.key === "Enter") {
      if (!lista.hidden && resultados[indiceActivo]) {
        e.preventDefault();
        elegir(resultados[indiceActivo]);
      }
    } else if (e.key === "Escape") {
      cerrar();
    }
  });

  // Al salir del campo: si no se eligió ningún producto de la lista,
  // se borra el texto para no dejar un nombre que no corresponde a un id.
  input.addEventListener("blur", () => {
    cerrar();
    if (!oculto.value) input.value = "";
  });
}

// Buscador del formulario: al elegir (o borrar) el producto se actualiza
// la unidad base y se recalcula el factor.
crearAutocompletar({
  input: inpBuscarProducto,
  oculto: selProducto,
  lista: listaProductos,
  onCambio: (producto) => {
    productoElegido = producto;
    sugerirFactor();
  },
});

// Buscador del filtro de la lista: al elegir (o borrar) el producto se
// vuelve a mostrar la tabla. Sin producto elegido se muestran todas.
crearAutocompletar({
  input: inpFiltroBuscar,
  oculto: filtroProducto,
  lista: listaFiltro,
  onCambio: () => mostrarPresentaciones(),
});

// ================== CARGA INICIAL ==================
// Los productos ya NO se cargan aquí: se buscan en el servidor mientras
// el usuario escribe. Aquí solo se cargan las unidades de medida.
async function cargarDatos() {
  try {
    unidades = await cargarUnidades();
    selUnidad.innerHTML = opciones(unidades);

    sugerirFactor();
    await mostrarPresentaciones();
  } catch (err) {
    mostrarMensaje(err.message, "error");
  }
}

// ================== LISTA ==================
async function mostrarPresentaciones() {
  try {
    const lista = await cargarPresentaciones(filtroProducto.value);
    tabla.innerHTML = "";

    for (const p of lista) {
      const fila = document.createElement("tr");
      fila.append(
        celda(p.id),
        celda(p.producto_nombre),
        celda(p.unidad_nombre),
        celda(Number(p.factor), "num"),
        celda(Number(p.precio_venta).toFixed(2), "num"),
        celda(p.codigo_barras || "—", "codigo")
      );
      tabla.appendChild(fila);
    }

    sinDatos.hidden = lista.length > 0;
  } catch (err) {
    mostrarMensaje(err.message, "error");
  }
}

// ================== FORMULARIO ==================
// Si la unidad elegida es la unidad base del producto, el factor siempre es 1
let factorBloqueado = false;

function esUnidadBase() {
  return !!productoElegido && String(productoElegido.unidad_base_id) === selUnidad.value;
}

function sugerirFactor() {
  if (esUnidadBase()) {
    inpFactor.value = 1;
    inpFactor.disabled = true;
    factorBloqueado = true;
    pistaFactor.textContent = "Es la unidad base del producto: el factor siempre es 1.";
  } else {
    if (factorBloqueado) inpFactor.value = ""; // quitamos el 1 automático
    inpFactor.disabled = false;
    factorBloqueado = false;
    pistaFactor.textContent = "";
  }
}

function limpiarFormulario(borrarMensaje = true) {
  inpFactor.value = "";
  inpPrecio.value = "";
  sugerirFactor();
  if (borrarMensaje) ocultarMensaje();
}

function leerFormulario() {
  const productoId = Number(selProducto.value);
  const unidadId = Number(selUnidad.value);
  const factor = Number(inpFactor.value);
  const precio = Number(inpPrecio.value);

  if (!productoId) throw new Error("Elige un producto");
  if (!unidadId) throw new Error("Elige una unidad de medida");
  if (!(factor > 0)) throw new Error("El factor debe ser mayor a 0");
  if (inpPrecio.value === "" || precio < 0) {
    throw new Error("Escribe un precio de venta (0 o más)");
  }

  return { producto_id: productoId, unidad_id: unidadId, factor: factor, precio_venta: precio };
}

async function guardar() {
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
    const datos = await crearPresentacion(cuerpo);

    mostrarMensaje(
      `Presentación creada: ${datos.producto_nombre} - ${datos.unidad_nombre} ` +
        `(trae ${Number(datos.factor)} unidades)`,
      "ok"
    );
    limpiarFormulario(false);
    await mostrarPresentaciones();
  } catch (err) {
    // TypeError = el navegador no pudo llegar al servidor
    mostrarMensaje(
      err instanceof TypeError ? "No se pudo conectar con el servidor" : err.message,
      "error"
    );
  } finally {
    btnGuardar.disabled = false;
    btnGuardar.textContent = "Guardar presentación";
  }
}

// ================== EVENTOS ==================
btnGuardar.addEventListener("click", guardar);
btnLimpiar.addEventListener("click", () => limpiarFormulario(true));
selUnidad.addEventListener("change", sugerirFactor);
document.addEventListener("DOMContentLoaded", cargarDatos);