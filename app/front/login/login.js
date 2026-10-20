//app\front\login\login.js
const PAGINA_INICIO = "../dashboard/dashboard.html";

const campoUsuario = document.getElementById("username");
const campoClave = document.getElementById("password");
const mensaje = document.getElementById("mensaje");
const botonEntrar = document.getElementById("btnEntrar");

async function entrar() {
    mensaje.textContent = "";
    botonEntrar.disabled = true;
    try {
        await iniciarSesion(campoUsuario.value, campoClave.value);
        window.location.href = PAGINA_INICIO;
    } catch (error) {
        mensaje.textContent = error.message;
    } finally {
        botonEntrar.disabled = false;
    }
}

botonEntrar.addEventListener("click", entrar);
campoClave.addEventListener("keydown", function (e) {
    if (e.key === "Enter") entrar();
});