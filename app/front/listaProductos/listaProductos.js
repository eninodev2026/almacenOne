const cuerpoTabla = document.getElementById("cuerpoTabla");
const mensaje = document.getElementById("mensaje");
const campoFiltro = document.getElementById("filtro");
const listaSugerencias = document.getElementById("sugerencias");
const contador = document.getElementById("contador");

// Aquí se guardan todos los productos que trae el servidor
let todosLosProductos = [];

// Quita mayúsculas y tildes para comparar mejor ("Café" = "cafe")
function normalizar(texto) {
    return texto.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

// Crea una celda de texto
function crearCelda(texto) {
    const celda = document.createElement("td");
    celda.textContent = texto;
    return celda;
}

// Dibuja las filas de la tabla con los productos que le pasemos
function dibujarTabla(productos) {
    cuerpoTabla.innerHTML = "";

    productos.forEach((producto) => {
        const fila = document.createElement("tr");
        fila.appendChild(crearCelda(producto.codigo));
        fila.appendChild(crearCelda(producto.nombre));
        fila.appendChild(crearCelda(producto.categoria_nombre));
        fila.appendChild(crearCelda(producto.unidad_base_nombre));

        const celdaAcciones = document.createElement("td");
        const enlaceEditar = document.createElement("a");
        enlaceEditar.textContent = "Editar";
        enlaceEditar.href = "../editarProducto/editarProducto.html?id=" + producto.id;
        celdaAcciones.appendChild(enlaceEditar);
        fila.appendChild(celdaAcciones);

        cuerpoTabla.appendChild(fila);
    });

    contador.textContent = "Mostrando " + productos.length + " de " + todosLosProductos.length;
    mensaje.textContent = productos.length === 0 ? "No hay productos que coincidan con la búsqueda." : "";
}

// Filtra mientras el usuario escribe: todas las palabras deben aparecer
function aplicarFiltro() {
    const palabras = normalizar(campoFiltro.value).split(" ").filter(Boolean);

    const filtrados = todosLosProductos.filter((producto) => {
        const texto = normalizar(
            producto.codigo + " " + producto.nombre + " " +
            producto.categoria_nombre + " " + producto.unidad_base_nombre
        );
        return palabras.every((palabra) => texto.includes(palabra));
    });

    dibujarTabla(filtrados);
}

// Llena las sugerencias del autocompletado
function llenarSugerencias() {
    todosLosProductos.forEach((producto) => {
        const opcion = document.createElement("option");
        opcion.value = producto.nombre;
        opcion.label = producto.codigo;
        listaSugerencias.appendChild(opcion);
    });
}

// Trae los productos y los muestra
async function mostrarProductos() {
    try {
        todosLosProductos = await cargarProductosConNombres();

        if (todosLosProductos.length === 0) {
            mensaje.textContent = "No hay productos registrados.";
            return;
        }

        llenarSugerencias();
        dibujarTabla(todosLosProductos);
    } catch (error) {
        mensaje.textContent = error.message;
    }
}

campoFiltro.addEventListener("input", aplicarFiltro);
document.addEventListener("DOMContentLoaded", mostrarProductos);