// Usa las funciones de ..\api.js (cargarSalidas y anularSalida).
// Ahí vive la dirección de la API.

// ================== ELEMENTOS ==================
const cuerpoTabla = document.getElementById("filas");
const filtroEstado = document.getElementById("filtroEstado");
const caja = document.getElementById("mensaje");

const fondoModal = document.getElementById("modal");
const modalTitulo = document.getElementById("modalTitulo");
const inputMotivo = document.getElementById("motivo");
const cajaErrorModal = document.getElementById("modalError");
const btnConfirmar = document.getElementById("btnConfirmar");
const btnCancelar = document.getElementById("btnCancelar");

let salidas = [];
let salidaElegida = null;

// ================== UTILIDADES ==================
function mostrarMensaje(texto, tipo) {
  caja.textContent = texto;
  caja.className = tipo; // "ok" o "error"
}

function ocultarMensaje() {
  caja.textContent = "";
  caja.className = "";
}

function mostrarErrorModal(texto) {
  cajaErrorModal.textContent = texto;
  cajaErrorModal.className = "error";
}

function ocultarErrorModal() {
  cajaErrorModal.textContent = "";
  cajaErrorModal.className = "";
}

function formatearFecha(valor) {
  if (!valor) return "";
  return new Date(valor).toLocaleString("es-SV", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function crearCelda(texto, clase) {
  const td = document.createElement("td");
  td.textContent = texto;
  if (clase) td.className = clase;
  return td;
}

// ================== LISTA ==================
function pintarTabla() {
  const estadoElegido = filtroEstado.value;
  const lista = salidas.filter(function (s) {
    return estadoElegido === "TODAS" || s.estado === estadoElegido;
  });

  cuerpoTabla.innerHTML = "";

  if (lista.length === 0) {
    const fila = document.createElement("tr");
    const celda = crearCelda("No hay salidas para mostrar", "sin-datos");
    celda.colSpan = 6;
    fila.appendChild(celda);
    cuerpoTabla.appendChild(fila);
    return;
  }

  lista.forEach(function (salida) {
    const fila = document.createElement("tr");

    fila.appendChild(crearCelda(salida.id));
    fila.appendChild(crearCelda(formatearFecha(salida.fecha)));
    fila.appendChild(crearCelda(salida.bodega_nombre));
    fila.appendChild(crearCelda(salida.productos, "col-numero"));

    // Estado
    const celdaEstado = document.createElement("td");
    const etiqueta = document.createElement("span");
    etiqueta.className = "estado " + salida.estado.toLowerCase();
    etiqueta.textContent = salida.estado === "ANULADO" ? "Anulada" : "Activa";
    celdaEstado.appendChild(etiqueta);
    fila.appendChild(celdaEstado);

    // Anulación: botón si está activa, motivo y fecha si ya se anuló
    const celdaAccion = document.createElement("td");
    if (salida.estado === "ACTIVO") {
      const boton = document.createElement("button");
      boton.type = "button";
      boton.className = "btn-anular";
      boton.textContent = "Anular";
      boton.addEventListener("click", function () {
        abrirModal(salida);
      });
      celdaAccion.appendChild(boton);
    } else {
      const detalle = document.createElement("div");
      detalle.className = "detalle-anulacion";
      const motivo = document.createElement("strong");
      motivo.textContent = salida.motivo_anulacion || "";
      detalle.appendChild(motivo);
      detalle.appendChild(
        document.createTextNode(" — " + formatearFecha(salida.fecha_anulacion))
      );
      celdaAccion.appendChild(detalle);
    }
    fila.appendChild(celdaAccion);

    cuerpoTabla.appendChild(fila);
  });
}

async function cargarLista() {
  try {
    salidas = await cargarSalidas();
    pintarTabla();
  } catch (err) {
    mostrarMensaje(
      err instanceof TypeError ? "No se pudo conectar con el servidor" : err.message,
      "error"
    );
  }
}

// ================== VENTANA DE CONFIRMACIÓN ==================
function abrirModal(salida) {
  salidaElegida = salida;
  modalTitulo.textContent = "Anular salida N.º " + salida.id;
  inputMotivo.value = "";
  ocultarErrorModal();
  fondoModal.classList.add("abierto");
  inputMotivo.focus();
}

function cerrarModal() {
  fondoModal.classList.remove("abierto");
  salidaElegida = null;
}

async function confirmarAnulacion() {
  ocultarErrorModal();

  const motivo = inputMotivo.value.trim();
  if (motivo.length < 5) {
    mostrarErrorModal("Escribe un motivo de al menos 5 caracteres");
    return;
  }

  btnConfirmar.disabled = true;
  btnConfirmar.textContent = "Anulando...";

  try {
    const numero = salidaElegida.id;
    await anularSalida(numero, motivo);
    cerrarModal();
    ocultarMensaje();
    mostrarMensaje("Salida N.º " + numero + " anulada. El stock fue devuelto a la bodega.", "ok");
    await cargarLista();
  } catch (err) {
    mostrarErrorModal(
      err instanceof TypeError ? "No se pudo conectar con el servidor" : err.message
    );
  } finally {
    btnConfirmar.disabled = false;
    btnConfirmar.textContent = "Confirmar anulación";
  }
}

// ================== EVENTOS ==================
filtroEstado.addEventListener("change", pintarTabla);
btnConfirmar.addEventListener("click", confirmarAnulacion);
btnCancelar.addEventListener("click", cerrarModal);
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape" && fondoModal.classList.contains("abierto")) cerrarModal();
});
document.addEventListener("DOMContentLoaded", cargarLista);