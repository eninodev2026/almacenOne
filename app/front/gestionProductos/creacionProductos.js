
// Buscamos el formulario de productos
const formularioDeProductos =
    document.getElementById("frmProductos");


// Esperamos a que la página termine de cargar
document.addEventListener("DOMContentLoaded", async () => {

    // Traemos las categorías
    const categorias =
        await cargarCategorias();


    // Recorremos las categorías
    categorias.forEach((categoria) => {

        // Creamos una opción
        const opcionDeCategoria =
            document.createElement("option");

        // Ponemos el ID de la categoría
        opcionDeCategoria.value =
            categoria.id;

        // Ponemos el nombre de la categoría
        opcionDeCategoria.text =
            categoria.nombre;

        // Agregamos la categoría al formulario
        document
            .getElementById("categoria")
            .appendChild(opcionDeCategoria);
    });


    // Traemos las unidades
    const unidades =
        await cargarUnidades();


    // Recorremos las unidades
    unidades.forEach((unidad) => {

        // Creamos una opción
        const opcionDeUnidad =
            document.createElement("option");

        // Ponemos el ID de la unidad
        opcionDeUnidad.value =
            unidad.id;

        // Ponemos el nombre de la unidad
        opcionDeUnidad.text =
            unidad.nombre;

        // Agregamos la unidad al formulario
        document
            .getElementById("unidadMedida")
            .appendChild(opcionDeUnidad);
    });

});


// Esperamos a que el usuario envíe el formulario
formularioDeProductos.addEventListener(
    "submit",
    async (evento) => {

        // Evitamos que la página se recargue
        evento.preventDefault();


        // Guardamos los datos escritos en el formulario
        const datosIngresoProducto = {

            // Guardamos el código
            codigo:
                document.getElementById("codigo").value,

            // Guardamos el nombre
            nombre:
                document.getElementById("nombre").value,

            // Guardamos la categoría
            categoria_id:
                Number(
                    document.getElementById("categoria").value
                ),

            // Guardamos la unidad
            unidad_base_id:
                Number(
                    document.getElementById("unidadMedida").value
                )
        };


        // Mostramos los datos que vamos a enviar
        console.log(
            "Datos del producto:",
            datosIngresoProducto
        );


        // Creamos el producto
        const respuestaDelServidor =
            await crearProducto(
                datosIngresoProducto
            );


        // Buscamos el lugar donde mostraremos la respuesta
        const lugarParaMostrarRespuesta =
            document.getElementById("respuestaApi");


        // Convertimos la respuesta en texto
        const respuestaEnTexto =
            JSON.stringify(respuestaDelServidor);


        // Mostramos la respuesta en la página
        lugarParaMostrarRespuesta.textContent =
            respuestaEnTexto;
    }
);

