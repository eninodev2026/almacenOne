// app/front/reportes/gestionReportes.js
// Pantalla que centraliza la descarga de reportes.
// Para agregar un reporte nuevo: agrega un objeto más en la lista REPORTES.
(function () {
    "use strict";

    const ICONOS = {
        bodega:
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M22 8.35V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8.35A2 2 0 0 1 3.26 6.5l8-3.2a2 2 0 0 1 1.48 0l8 3.2A2 2 0 0 1 22 8.35Z"/>' +
            '<path d="M6 18h12"/><path d="M6 14h12"/><rect width="12" height="12" x="6" y="10"/></svg>',
        grafico:
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/></svg>',
        dinero:
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
        alerta:
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',    
        traslado:
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/></svg>',            

        descargar:
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>'
    };

    // Lista de reportes disponibles. Cada "descargar" llama a una función de api.js
    const REPORTES = [
        {
            titulo: "Stock por bodega",
            descripcion: "Excel con una hoja por cada bodega: código, nombre, tipo de presentación y cantidad disponible, con la fecha del reporte y el usuario que lo generó.",
            formato: "Excel (.xlsx)",
            icono: ICONOS.bodega,
            descargar: function () { return descargarReporteStockPorBodega(); }
        },
        {
            titulo: "Stock detallado",
            descripcion: "Excel con un resumen general y el detalle por producto y bodega: entradas, salidas, costo promedio, valor total y días en bodega.",
            formato: "Excel (.xlsx)",
            icono: ICONOS.grafico,
            descargar: function () { return descargarReporteStock(); }
        }, 
        
        {
            titulo: "Valor de inventario",
            descripcion: "Excel con el valor del inventario por producto y bodega: cantidad, costo promedio y valor total, con filtros y el total general.",
            formato: "Excel (.xlsx)",
            icono: ICONOS.dinero,
            descargar: function () { return descargarReporteValorInventario(); }
        },
        {
            titulo: "Productos agotados",
            descripcion: "Excel con los productos que ya no tienen existencias en ninguna bodega: código, nombre y cantidad total, con filtros y el total de productos agotados.",
            formato: "Excel (.xlsx)",
            icono: ICONOS.alerta,
            descargar: function () { return descargarReporteProductosAgotados(); }
        },
        
        {
            titulo: "Movimientos entre bodegas",
            descripcion: "Excel con los traslados entre bodegas: estado (despachado, recibido o rechazado), origen, destino, producto, cantidad, valor y observaciones, con filtros y el valor total.",
            formato: "Excel (.xlsx)",
            icono: ICONOS.traslado,
            descargar: function () { return descargarReporteMovimientosEntreBodegas(); }
        }
        

    ];

    const contenedorLista = document.getElementById("repLista");
    const cajaMensaje = document.getElementById("repMensaje");
    const cajaUsuario = document.getElementById("repUsuario");
    let temporizadorMensaje = null;

    function mostrarMensaje(texto, tipo) {
        clearTimeout(temporizadorMensaje);
        cajaMensaje.textContent = texto;
        cajaMensaje.className = "rep-mensaje " + (tipo === "exito" ? "rep-exito" : "rep-error");

        if (tipo === "exito") {
            temporizadorMensaje = setTimeout(function () {
                cajaMensaje.className = "rep-mensaje rep-oculto";
            }, 5000);
        }
    }

    function crearTarjeta(reporte) {
        const tarjeta = document.createElement("article");
        tarjeta.className = "rep-tarjeta";

        const icono = document.createElement("div");
        icono.className = "rep-icono";
        icono.innerHTML = reporte.icono;

        const titulo = document.createElement("h2");
        titulo.className = "rep-tarjeta-titulo";
        titulo.textContent = reporte.titulo;

        const descripcion = document.createElement("p");
        descripcion.className = "rep-tarjeta-descripcion";
        descripcion.textContent = reporte.descripcion;

        const formato = document.createElement("span");
        formato.className = "rep-formato";
        formato.textContent = reporte.formato;

        const boton = document.createElement("button");
        boton.type = "button";
        boton.className = "rep-boton";
        boton.innerHTML = ICONOS.descargar;
        const textoBoton = document.createElement("span");
        textoBoton.textContent = "Descargar";
        boton.appendChild(textoBoton);

        boton.addEventListener("click", async function () {
            if (boton.disabled) {
                return;
            }
            boton.disabled = true;
            textoBoton.textContent = "Generando...";

            try {
                await reporte.descargar();
                mostrarMensaje("Reporte descargado: " + reporte.titulo, "exito");
            } catch (error) {
                mostrarMensaje(error.message || "No se pudo descargar el reporte", "error");
            } finally {
                boton.disabled = false;
                textoBoton.textContent = "Descargar";
            }
        });

        tarjeta.appendChild(icono);
        tarjeta.appendChild(titulo);
        tarjeta.appendChild(descripcion);
        tarjeta.appendChild(formato);
        tarjeta.appendChild(boton);
        return tarjeta;
    }

    async function mostrarUsuario() {
        try {
            const sesion = await obtenerSesion();
            cajaUsuario.textContent = sesion.nombre + (sesion.rol ? " · " + sesion.rol : "");
        } catch (error) {
            // Si la sesión expiró, api.js ya redirige al login
        }
    }

    REPORTES.forEach(function (reporte) {
        contenedorLista.appendChild(crearTarjeta(reporte));
    });
    mostrarUsuario();
})();