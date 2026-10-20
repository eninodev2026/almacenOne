const formulario = document.getElementById("frmEditarProducto");
const mensaje = document.getElementById("mensaje");

// El id del producto viene en la dirección: ...editarProducto.html?id=5
const productoId = Number(new URLSearchParams(window.location.search).get("id"));

// Llena un <select> con opciones
function llenarSelect(idSelect, elementos) {
    const select = document.getElementById(idSelect);
    elementos.forEach((elemento) => {
        const opcion = document.createElement("option");
        opcion.value = elemento.id;
        opcion.text = elemento.nombre;
        select.appendChild(opcion);
    });
}

// Carga las listas y los datos actuales del producto
async function cargarFormulario() {
    try {
        llenarSelect("categoria", await cargarCategorias());
        llenarSelect("unidadMedida", await cargarUnidades());

        const productos = await cargarProductosConNombres();
        const producto = productos.find((p) => p.id === productoId);

        if (!producto) {
            mensaje.textContent = "El producto no existe.";
            return;
        }

        document.getElementById("codigo").value = producto.codigo;
        document.getElementById("nombre").value = producto.nombre;
        document.getElementById("categoria").value = producto.categoria_id;
        document.getElementById("unidadMedida").value = producto.unidad_base_id;
    } catch (error) {
        mensaje.textContent = error.message;
    }
}

// Guarda los cambios
formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensaje.textContent = "";

    const datos = {
        codigo: document.getElementById("codigo").value,
        nombre: document.getElementById("nombre").value,
        categoria_id: Number(document.getElementById("categoria").value),
        unidad_base_id: Number(document.getElementById("unidadMedida").value)
    };

    try {
        await editarProducto(productoId, datos);
        mensaje.textContent = "Producto actualizado correctamente.";
    } catch (error) {
        mensaje.textContent = error.message;
    }
});

document.addEventListener("DOMContentLoaded", cargarFormulario);