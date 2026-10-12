// app/front/api.js
// Dirección donde está funcionando nuestra API
const url_api = "http://localhost:8000";

// Carpeta base del front (para redirigir al login desde cualquier pantalla)
const BASE_FRONT = document.currentScript ? new URL(".", document.currentScript.src).href : "";

// Todas las peticiones pasan por aquí: envía la cookie de sesión, el header
// anti-CSRF y manda al login si la sesión expiró.
async function fetchApi(ruta, opciones) {
    const config = Object.assign({}, opciones);
    config.credentials = "include";
    config.headers = Object.assign({ "X-Requested-With": "fetch" }, config.headers);

    const respuesta = await fetch(url_api + ruta, config);

    if (respuesta.status === 401 && ruta !== "/auth/login") {
        window.location.href = BASE_FRONT + "login/login.html";
        throw new Error("Tu sesión expiró. Inicia sesión de nuevo.");
    }
    return respuesta;
}

// ================== SESIÓN ==================

async function iniciarSesion(username, password) {
    return await enviarDatosALaApi("/auth/login", { username: username, password: password });
}

async function cerrarSesion() {
    await fetchApi("/auth/logout", { method: "POST" });
    window.location.href = BASE_FRONT + "login/login.html";
}

// Devuelve { id, username, nombre, rol, permisos: [...] }
async function obtenerSesion() {
    return await pedirListaALaApi("/auth/me");
}

// Lista las sesiones abiertas (requiere permiso de gestión de usuarios)
async function cargarSesionesActivas() {
    return await pedirListaALaApi("/usuarios/sesiones");
}

// Cierra una sesión ajena (requiere permiso de gestión de usuarios)
async function cerrarSesionRemota(sesionId) {
    return await enviarDatosALaApi("/usuarios/sesiones/" + sesionId + "/cerrar", {});
}

// Trae las categorías desde la API
async function cargarCategorias() {
    const respuestaDeCategorias = await fetchApi("/categorias/");
    const categorias = await respuestaDeCategorias.json();
    return categorias;
}

// Trae las unidades desde la API
async function cargarUnidades() {
    const respuestaDeUnidades = await fetchApi("/unidades/");
    const unidades = await respuestaDeUnidades.json();
    return unidades;
}

// Envía los datos para crear un producto
async function crearProducto(datosIngresoProducto) {
    const respuestaDelEndpoint = await fetchApi(
        "/productos/",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(datosIngresoProducto)
        }
    );
    const datosQueRespondioLaApi = await respuestaDelEndpoint.json();
    return datosQueRespondioLaApi;
}

// ================== AYUDANTES ==================

function leerMensajeDeError(datosDeError) {
    if (!datosDeError || !datosDeError.detail) {
        return "Ocurrió un error inesperado";
    }
    if (typeof datosDeError.detail === "string") {
        return datosDeError.detail;
    }
    if (Array.isArray(datosDeError.detail)) {
        return datosDeError.detail.map(function (error) {
            return error.msg;
        }).join(". ");
    }
    return "Ocurrió un error inesperado";
}

// Pide una lista a la API. El parámetro "signal" es opcional: sirve para
// poder cancelar la petición si el usuario sigue escribiendo.
async function pedirListaALaApi(ruta, signal) {
    const respuesta = await fetchApi(ruta, { signal: signal });
    if (!respuesta.ok) {
        throw new Error("No se pudo cargar " + ruta);
    }
    return await respuesta.json();
}
async function enviarDatosALaApi(ruta, datos) {
    const respuesta = await fetchApi(
        ruta,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(datos)
        }
    );

    const datosQueRespondioLaApi = await respuesta.json().catch(function () {
        return null;
    });

    if (!respuesta.ok) {
        throw new Error(leerMensajeDeError(datosQueRespondioLaApi));
    }

    return datosQueRespondioLaApi;
}

// ================== BODEGAS, PRODUCTOS, PRESENTACIONES Y SALIDAS ==================

// Envía los datos para crear una bodega
async function crearBodega(datosIngresoBodega) {
    return await enviarDatosALaApi("/bodegas/", datosIngresoBodega);
}

async function cargarBodegas() {
    return await pedirListaALaApi("/bodegas/");
}

// Sin parámetros: trae TODOS los productos (las otras pantallas la usan así).
// Con { texto, limite, signal }: pide al servidor solo los productos que
// coinciden con el texto (por nombre o código), máximo "limite" resultados.
async function cargarProductos(opciones) {
    if (!opciones) {
        return await pedirListaALaApi("/productos/");
    }

    const limite = opciones.limite || 10;
    const ruta =
        "/productos/buscar?q=" + encodeURIComponent(opciones.texto || "") +
        "&limite=" + limite;

    return await pedirListaALaApi(ruta, opciones.signal);
}

async function cargarPresentaciones(productoId) {
    let ruta = "/presentaciones/";
    if (productoId) {
        ruta = ruta + "?producto_id=" + productoId;
    }
    return await pedirListaALaApi(ruta);
}

async function crearPresentacion(datosIngresoPresentacion) {
    return await enviarDatosALaApi("/presentaciones/", datosIngresoPresentacion);
}

async function crearSalida(datosIngresoSalida) {
    return await enviarDatosALaApi("/salidas/", datosIngresoSalida);
}

// ================== PROVEEDORES Y COMPRAS ==================

async function cargarProveedores() {
    return await pedirListaALaApi("/proveedores/");
}

async function crearCompra(datosIngresoCompra) {
    return await enviarDatosALaApi("/compras/", datosIngresoCompra);
}

// ================== INVENTARIO (NUEVO) ==================

async function buscarInventario(filtros) {
    const params = new URLSearchParams();
    
    if (filtros.texto) params.append('texto', filtros.texto);
    if (filtros.bodegaId) params.append('bodega_id', filtros.bodegaId);
    if (filtros.stockMin !== null && filtros.stockMin !== undefined) params.append('stock_min', filtros.stockMin);
    if (filtros.stockMax !== null && filtros.stockMax !== undefined) params.append('stock_max', filtros.stockMax);
    if (filtros.fechaDesde) params.append('fecha_desde', filtros.fechaDesde);
    if (filtros.fechaHasta) params.append('fecha_hasta', filtros.fechaHasta);
    if (filtros.diasMax !== null && filtros.diasMax !== undefined) params.append('dias_max', filtros.diasMax);

    // Construimos la ruta. La barra diagonal final (/) es CRÍTICA para evitar 
    // la redirección 307 de FastAPI que rompe el CORS.
    const queryString = params.toString() ? `?${params.toString()}` : '';
    const ruta = `/inventario/${queryString}`;

    const respuesta = await fetchApi(ruta);

    if (!respuesta.ok) {
        const datosError = await respuesta.json().catch(() => ({}));
        throw new Error(leerMensajeDeError(datosError) || "No se pudo cargar el inventario");
    }

    return await respuesta.json();
}

// ================== PROVEEDORES Y COMPRAS ==================
async function crearProveedor(datosIngresoProveedor) {
    return await enviarDatosALaApi("/proveedores/", datosIngresoProveedor);
}


// Descarga la hoja de salida (PDF) de un movimiento
async function descargarHojaSalida(movimientoId) {
    const respuesta = await fetchApi("/salidas/" + movimientoId + "/pdf");

    if (!respuesta.ok) {
        const datosError = await respuesta.json().catch(function () {
            return null;
        });
        throw new Error(leerMensajeDeError(datosError));
    }

    const archivo = await respuesta.blob();
    const direccionTemporal = URL.createObjectURL(archivo);

    const enlace = document.createElement("a");
    enlace.href = direccionTemporal;
    enlace.download = "salida_" + movimientoId + ".pdf";
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();

    setTimeout(function () {
        URL.revokeObjectURL(direccionTemporal);
    }, 1000);
}


// ================== ANULACIÓN DE SALIDAS ==================

// Trae la lista de salidas (activas y anuladas)
async function cargarSalidas() {
    return await pedirListaALaApi("/salidas/");
}

// Anula una salida y le devuelve el stock a la bodega
async function anularSalida(movimientoId, motivo) {
    const respuesta = await fetchApi(
        "/salidas/" + movimientoId + "/anular",
        {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ motivo: motivo })
        }
    );

    const datosQueRespondioLaApi = await respuesta.json().catch(function () {
        return null;
    });

    if (!respuesta.ok) {
        throw new Error(leerMensajeDeError(datosQueRespondioLaApi));
    }

    return datosQueRespondioLaApi;
}


// Descarga el reporte de stock en Excel (endpoint /reportes/stock/excel)
async function descargarReporteStock() {
    const respuesta = await fetchApi("/reportes/stock/excel");

    if (!respuesta.ok) {
        const datosError = await respuesta.json().catch(function () {
            return null;
        });
        throw new Error(leerMensajeDeError(datosError));
    }

    const archivo = await respuesta.blob();
    const direccionTemporal = URL.createObjectURL(archivo);

    const enlace = document.createElement("a");
    enlace.href = direccionTemporal;
    enlace.download = "stock_" + new Date().toISOString().slice(0, 10) + ".xlsx";
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();

    setTimeout(function () {
        URL.revokeObjectURL(direccionTemporal);
    }, 1000);
}

// Envía los datos para crear una categoría
async function crearCategoria(datosIngresoCategoria) {
    return await enviarDatosALaApi("/categorias/", datosIngresoCategoria);
}