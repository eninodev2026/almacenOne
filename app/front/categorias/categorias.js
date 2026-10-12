// app/front/categorias/categorias.js
// Pantalla de categorías: solo maneja la interfaz. Las peticiones viven en api.js

const campoNombre = document.getElementById("nombreCategoria");
const botonGuardar = document.getElementById("btnGuardar");
const cajaRespuesta = document.getElementById("respuestaApi");
const listaCategorias = document.getElementById("listaCategorias");
const totalCategorias = document.getElementById("totalCategorias");
const seccionFormulario = document.getElementById("seccionFormulario");

function mostrarMensaje(texto, tipo) {
    cajaRespuesta.textContent = texto;
    cajaRespuesta.className = tipo;
}

async function pintarCategorias() {
    const categorias = await cargarCategorias();

    if (!Array.isArray(categorias)) {
        throw new Error(
            categorias && typeof categorias.detail === "string"
                ? categorias.detail
                : "No se pudieron cargar las categorías"
        );
    }

    listaCategorias.replaceChildren();
    totalCategorias.textContent = categorias.length;

    categorias.forEach(function (categoria) {
        const item = document.createElement("li");
        item.textContent = categoria.nombre;
        item.style.padding = "10px 0";
        item.style.borderBottom = "1px solid var(--borde)";
        listaCategorias.appendChild(item);
    });
}

async function guardarCategoria() {
    const nombre = campoNombre.value.trim();

    if (!nombre) {
        mostrarMensaje("Escribe el nombre de la categoría", "error");
        return;
    }

    botonGuardar.disabled = true;
    try {
        await crearCategoria({ nombre: nombre });
        campoNombre.value = "";
        mostrarMensaje("Categoría creada correctamente", "ok");
        await pintarCategorias();
    } catch (error) {
        mostrarMensaje(error.message, "error");
    } finally {
        botonGuardar.disabled = false;
    }
}

async function iniciar() {
    try {
        // Solo quien tiene permiso de catálogo ve el formulario
        const sesion = await obtenerSesion();
        if (!sesion.permisos.includes("catalogo.gestionar")) {
            seccionFormulario.style.display = "none";
        }
        await pintarCategorias();
    } catch (error) {
        mostrarMensaje(error.message, "error");
        seccionFormulario.style.display = "";
    }
}

botonGuardar.addEventListener("click", guardarCategoria);
campoNombre.addEventListener("keydown", function (e) {
    if (e.key === "Enter") guardarCategoria();
});
document.addEventListener("DOMContentLoaded", iniciar);