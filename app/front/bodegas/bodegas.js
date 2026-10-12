// Pantalla "Bodegas".
// Usa las funciones de ..\api.js (cargarBodegas y crearBodega).
// Ahí vive la dirección de la API.
//
// Qué hace esta pantalla:
//   1) Muestra la lista de bodegas que existen.
//   2) Permite crear una bodega nueva (nombre obligatorio, dirección opcional).

// ================== ELEMENTOS ==================
const inpNombre = document.getElementById("nombre");
const inpDireccion = document.getElementById("direccion");
const btnGuardar = document.getElementById("btnGuardar");
const btnLimpiar = document.getElementById("btnLimpiar");
const caja = document.getElementById("mensaje");
const tabla = document.getElementById("tablaBodegas");
const sinDatos = document.getElementById("sinDatos");

// ================== UTILIDADES ==================
// Muestra un mensaje bajo el formulario. tipo: "ok" o "error"
function mostrarMensaje(texto, tipo) {
  caja.textContent = texto;
  caja.className = tipo;
}

function ocultarMensaje() {
  caja.textContent = "";
  caja.className = "";
}

// Crea una celda <td> con texto. "clase" es opcional (ej: "num")
function celda(texto, clase) {
  const td = document.createElement("td");
  td.textContent = texto;
  if (clase) td.className = clase;
  return td;
}

// ================== LISTA ==================
// Pide las bodegas a la API y las dibuja en la tabla
async function mostrarBodegas() {
  try {
    const lista = await cargarBodegas();
    tabla.innerHTML = "";

    for (const b of lista) {
      const fila = document.createElement("tr");
      fila.append(
        celda(b.id),
        celda(b.nombre),
        celda(b.direccion || "—")
      );
      tabla.appendChild(fila);
    }

    // Si no hay bodegas se muestra el aviso "No hay bodegas para mostrar"
    sinDatos.hidden = lista.length > 0;
  } catch (err) {
    mostrarMensaje(err.message, "error");
  }
}

// ================== FORMULARIO ==================
function limpiarFormulario(borrarMensaje = true) {
  inpNombre.value = "";
  inpDireccion.value = "";
  if (borrarMensaje) ocultarMensaje();
  inpNombre.focus();
}

// Lee y valida el formulario. Si algo está mal lanza un Error con el
// mensaje que se le mostrará al usuario.
function leerFormulario() {
  const nombre = inpNombre.value.trim();
  const direccion = inpDireccion.value.trim();

  if (!nombre) throw new Error("Escribe el nombre de la bodega");

  // La dirección es opcional: si está vacía se envía null (como espera la API)
  return { nombre: nombre, direccion: direccion || null };
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

  // Bloqueamos el botón para evitar guardar dos veces con un doble clic
  btnGuardar.disabled = true;
  btnGuardar.textContent = "Guardando...";

  try {
    const datos = await crearBodega(cuerpo);

    mostrarMensaje(`Bodega creada: ${datos.nombre}`, "ok");
    limpiarFormulario(false);
    await mostrarBodegas();
  } catch (err) {
    // TypeError = el navegador no pudo llegar al servidor
    mostrarMensaje(
      err instanceof TypeError ? "No se pudo conectar con el servidor" : err.message,
      "error"
    );
  } finally {
    btnGuardar.disabled = false;
    btnGuardar.textContent = "Guardar bodega";
  }
}

// ================== EVENTOS ==================
btnGuardar.addEventListener("click", guardar);
btnLimpiar.addEventListener("click", () => limpiarFormulario(true));

// Presionar Enter dentro de cualquiera de los dos campos también guarda
[inpNombre, inpDireccion].forEach((input) => {
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") guardar();
  });
});

document.addEventListener("DOMContentLoaded", mostrarBodegas);