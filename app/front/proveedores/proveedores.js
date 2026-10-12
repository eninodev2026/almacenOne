const frmProveedores = document.getElementById("frmProveedores");
const respuestaApi = document.getElementById("respuestaApi");

frmProveedores.addEventListener("submit", async function (event) {
    event.preventDefault();

    const datosProveedor = {
        nombre: document.getElementById("nombre").value.trim(),
        nit: document.getElementById("nit").value.trim() || null,
        nrc: document.getElementById("nrc").value.trim() || null,
        telefono: document.getElementById("telefono").value.trim() || null,
        correo: document.getElementById("correo").value.trim() || null,
        direccion: document.getElementById("direccion").value.trim() || null
    };

    if (!datosProveedor.nombre) {
        mostrarMensaje("El nombre del proveedor es obligatorio.", "error");
        return;
    }

    try {
        const respuesta = await crearProveedor(datosProveedor);
        mostrarMensaje(`Proveedor "${respuesta.nombre}" registrado exitosamente.`, "exito");
        frmProveedores.reset();
    } catch (error) {
        mostrarMensaje(error.message, "error");
    }
});

function mostrarMensaje(texto, tipo) {
    respuestaApi.textContent = texto;
    respuestaApi.className = tipo;
}