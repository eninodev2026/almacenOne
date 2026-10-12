// app/front/dashboard/dashboard.js
// Dashboard principal - Carga estadísticas de todos los módulos

async function cargarEstadisticas() {
  try {
    // Cargar todos los datos en paralelo
    const [productos, bodegas, proveedores, categorias, presentaciones] = await Promise.all([
      cargarProductos(),
      cargarBodegas(),
      cargarProveedores(),
      cargarCategorias(),
      cargarPresentaciones()
    ]);

    // Actualizar contadores
    document.getElementById('contadorProductos').textContent = productos.length;
    document.getElementById('contadorBodegas').textContent = bodegas.length;
    document.getElementById('contadorProveedores').textContent = proveedores.length;
    document.getElementById('contadorCategorias').textContent = categorias.length;
    document.getElementById('statPresentaciones').textContent = presentaciones.length;

    // Cargar tipos de movimiento (necesitamos agregar esta función a api.js)
    try {
      const tiposMovimiento = await pedirListaALaApi('/tipos-movimiento/');
      document.getElementById('statTiposMovimiento').textContent = tiposMovimiento.length;
    } catch (err) {
      console.error('Error cargando tipos de movimiento:', err);
      document.getElementById('statTiposMovimiento').textContent = '0';
    }

  } catch (err) {
    console.error('Error cargando estadísticas:', err);
    alert('Error al cargar las estadísticas del dashboard');
  }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', cargarEstadisticas);

// Cerrar sesión
document.getElementById('btnCerrarSesion').addEventListener('click', cerrarSesion);


// ================== USUARIO ACTUAL Y USUARIOS CONECTADOS ==================

let usuarioActualId = null;

function formatearFecha(iso) {
  return new Date(iso).toLocaleString('es-SV');
}

function crearCelda(texto) {
  const celda = document.createElement('td');
  celda.textContent = texto;
  return celda;
}

async function cargarConectados() {
  try {
    const sesiones = await cargarSesionesActivas();
    const cuerpo = document.getElementById('cuerpoConectados');
    cuerpo.replaceChildren();
    document.getElementById('totalConectados').textContent = sesiones.length;

    sesiones.forEach(function (s) {
      const fila = document.createElement('tr');
      const esYo = s.usuario_id === usuarioActualId;

      fila.appendChild(crearCelda(s.nombre + ' (' + s.username + ')' + (esYo ? ' · tú' : '')));
      fila.appendChild(crearCelda(s.rol));
      fila.appendChild(crearCelda(formatearFecha(s.inicio)));
      fila.appendChild(crearCelda(formatearFecha(s.ultimo_uso)));
      fila.appendChild(crearCelda(s.ip || '-'));

      const celdaAccion = document.createElement('td');
      const boton = document.createElement('button');
      boton.type = 'button';
      boton.className = 'btn-cerrar-remota';
      boton.textContent = 'Cerrar sesión';
      boton.addEventListener('click', async function () {
        if (!confirm('¿Cerrar la sesión de ' + s.username + '?')) return;
        try {
          await cerrarSesionRemota(s.id);
          await cargarConectados();
        } catch (err) {
          alert(err.message);
        }
      });
      celdaAccion.appendChild(boton);
      fila.appendChild(celdaAccion);

      cuerpo.appendChild(fila);
    });
  } catch (err) {
    console.error('Error cargando usuarios conectados:', err);
  }
}

async function cargarSesionActual() {
  try {
    const sesion = await obtenerSesion();
    usuarioActualId = sesion.id;
    document.getElementById('usuarioActual').textContent = sesion.nombre;
    document.getElementById('rolActual').textContent = sesion.rol + ' · ' + sesion.username;

    // Solo quien puede gestionar usuarios ve quién está conectado
    if (sesion.permisos.includes('usuario.gestionar')) {
      document.getElementById('seccionConectados').style.display = '';
      await cargarConectados();
      setInterval(cargarConectados, 60000);
    }
  } catch (err) {
    console.error('Error cargando la sesión actual:', err);
  }
}

document.addEventListener('DOMContentLoaded', cargarSesionActual);