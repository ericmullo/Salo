"""Aplicación web sencilla con dos pantallas, sin dependencias externas."""

from html import escape
from email.message import EmailMessage
import json
import os
from pathlib import Path
import re
import runpy
import smtplib
import ssl
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

import psycopg

from database import actualizar_estado_correo, guardar_reclamo


STYLE = """
* { box-sizing: border-box; }
body {
    min-height: 100vh;
    margin: 0;
    display: grid;
    place-items: center;
    background: #fff8f6;
    color: #332a2a;
    font-family: Arial, Helvetica, sans-serif;
    text-align: center;
}
main { width: 100%; padding: 32px; }
h1 { margin: 0 0 28px; font-size: clamp(28px, 5vw, 42px); }
.boton-circular {
    display: inline-grid;
    place-items: center;
    width: 180px;
    height: 180px;
    border-radius: 50%;
    background: #df3030;
    color: white;
    font-size: 22px;
    font-weight: bold;
    text-decoration: none;
    box-shadow: 0 12px 25px rgba(160, 28, 28, .2);
    transition: transform .15s ease, background .15s ease;
}
.boton-circular:hover { transform: scale(1.05); background: #bc2020; }
.boton-circular:focus-visible, .volver:focus-visible,
.cupon:focus-visible, .cerrar:focus-visible, .reclamar:focus-visible,
.candado:focus-visible {
    outline: 3px solid #332a2a;
    outline-offset: 5px;
}
.volver { color: #bc2020; font-size: 18px; }
.pantalla-cupones { max-width: 900px; margin: auto; }
.cupones {
    min-height: 480px;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-template-rows: repeat(2, 1fr);
    gap: 24px;
    align-items: center;
    justify-items: center;
    perspective: 900px;
}
.cupon {
    width: min(100%, 170px);
    min-height: 90px;
    padding: 14px;
    border: 1px solid rgba(255, 255, 255, .38);
    border-bottom: 4px solid rgba(0, 0, 0, .22);
    border-radius: 20px;
    color: #fff;
    font: bold 20px Arial, Helvetica, sans-serif;
    cursor: pointer;
    text-shadow: 0 1px 2px rgba(0, 0, 0, .25);
    box-shadow: inset 0 2px 2px rgba(255, 255, 255, .35),
                0 9px 0 rgba(32, 25, 38, .4),
                0 17px 23px rgba(32, 25, 38, .22);
    transform-origin: center 12%;
    transform: perspective(500px) rotateX(8deg);
    animation: timbrar 5s ease-in-out infinite;
    transition: transform .18s ease, box-shadow .18s ease;
}
.cupon:nth-child(1) { background: linear-gradient(145deg, #f46a6a, #bd2323); justify-self: start; animation-delay: 0s; }
.cupon:nth-child(2) { background: linear-gradient(145deg, #5e91ee, #194595); align-self: end; animation-delay: -.8s; }
.cupon:nth-child(3) { background: linear-gradient(145deg, #59b68f, #176548); justify-self: end; animation-delay: -1.6s; }
.cupon:nth-child(4) { background: linear-gradient(145deg, #b484da, #65368e); align-self: start; animation-delay: -2.4s; }
.cupon:nth-child(5) { background: linear-gradient(145deg, #e09a54, #8d3e0e); justify-self: end; animation-delay: -3.2s; }
.cupon:nth-child(6) { background: linear-gradient(145deg, #e26da6, #892052); align-self: end; animation-delay: -4s; }
@keyframes timbrar {
    0%, 72%, 88%, 100% { transform: perspective(500px) rotateX(8deg) rotateZ(0); }
    75% { transform: perspective(500px) rotateX(8deg) rotateZ(-7deg); }
    78% { transform: perspective(500px) rotateX(8deg) rotateZ(7deg); }
    81% { transform: perspective(500px) rotateX(8deg) rotateZ(-5deg); }
    84% { transform: perspective(500px) rotateX(8deg) rotateZ(4deg); }
}
@media (hover: hover) {
    .cupon:hover {
        animation: none;
        transform: perspective(500px) rotateX(3deg) translateY(-4px) scale(1.04);
    }
}
.cupon:focus-visible {
    animation: none;
    transform: perspective(500px) rotateX(3deg) translateY(-4px) scale(1.04);
}
.cupon:active {
    animation: none;
    transform: perspective(500px) rotateX(0) translateY(7px);
    box-shadow: inset 0 2px 5px rgba(0, 0, 0, .15),
                0 2px 0 rgba(32, 25, 38, .4),
                0 5px 10px rgba(32, 25, 38, .18);
}
dialog {
    width: min(90vw, 420px);
    padding: 36px 24px;
    border: 0;
    border-radius: 24px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, .25);
    text-align: center;
}
dialog::backdrop { background: rgba(30, 20, 30, .55); }
dialog h2 { margin: 0 0 12px; font-size: clamp(26px, 7vw, 36px); }
.descripcion-cupon {
    margin: 0 0 20px;
    font-size: clamp(18px, 5vw, 22px);
    line-height: 1.4;
    overflow-wrap: anywhere;
}
.fecha-por-definir { margin: 0 0 20px; font-size: 16px; font-weight: bold; }
.candado {
    position: fixed;
    right: 20px;
    bottom: 20px;
    width: 56px;
    height: 56px;
    border: 0;
    border-radius: 50%;
    background: #332a2a;
    color: white;
    font-size: 26px;
    cursor: pointer;
    box-shadow: 0 6px 18px rgba(0, 0, 0, .25);
}
.aviso-candado {
    position: fixed;
    right: 20px;
    bottom: 86px;
    padding: 10px 16px;
    border-radius: 12px;
    background: #332a2a;
    color: white;
    font-weight: bold;
    box-shadow: 0 6px 18px rgba(0, 0, 0, .2);
}
.aviso-candado[hidden] { display: none; }
.cerrar {
    padding: 12px 28px;
    border: 0;
    border-radius: 12px;
    background: #332a2a;
    color: #fff;
    font: bold 16px Arial, Helvetica, sans-serif;
    cursor: pointer;
}
.reclamar {
    padding: 12px 28px;
    margin: 0 8px 12px;
    border: 0;
    border-radius: 12px;
    background: #d93636;
    color: #fff;
    font: bold 16px Arial, Helvetica, sans-serif;
    cursor: pointer;
}
.reclamar:disabled { opacity: .6; cursor: wait; }
.mensaje { min-height: 24px; margin: 8px 0 0; font-size: 15px; }
@media (max-width: 600px) {
    main { padding: 24px 16px; }
    .cupones {
        min-height: 0;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        grid-template-rows: none;
        gap: 18px 14px;
        margin: 30px auto;
    }
    .cupon, .cupon:nth-child(n) {
        width: 100%;
        min-height: 100px;
        justify-self: stretch;
        align-self: stretch;
        font-size: 17px;
    }
}
@media (max-width: 340px) {
    .cupones { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
    .cupon { animation: none; transition: none; }
}
"""


def pagina(titulo, contenido):
    """Construye el HTML que verá el navegador."""
    return f"""<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(titulo)}</title>
    <style>{STYLE}</style>
</head>
<body>
    <main>{contenido}</main>
</body>
</html>""".encode("utf-8")


NOMBRES_CUPONES = (
    "Primer cupón", "Segundo cupón", "Tercer cupón",
    "Cuarto cupón", "Quinto cupón", "Sexto cupón",
)

DESCRIPCIONES_CUPONES = (
    "Cupón válido para un biela",
    "Cupón válida para salir a comer (Burguer king nunca más)",
    "Cupón válido para ir al centro",
    "Cupón válido para ir al Starbucks",
    "Cupón válidos para unos Ferrero",
    "Cupón válido para vernos únicamente cuando estés triste",
)


def enviar_notificacion(numero, reclamo_id):
    """Envía el aviso por API en Render o por SMTP en local."""
    if os.getenv("RESEND_API_KEY"):
        return enviar_por_resend(numero, reclamo_id)
    return enviar_por_smtp(numero)


def enviar_por_resend(numero, reclamo_id):
    destinatario = os.getenv("NOTIFY_TO")
    if not destinatario:
        raise ValueError("Falta configurar NOTIFY_TO")
    remitente = os.getenv("RESEND_FROM", "Salo <onboarding@resend.dev>")
    contenido = (
        f"Se reclamó el {NOMBRES_CUPONES[numero - 1]} (cupón {numero}).\n"
        f"{DESCRIPCIONES_CUPONES[numero - 1]}\n"
        "Fecha por definir"
    )
    solicitud = Request(
        "https://api.resend.com/emails",
        data=json.dumps({
            "from": remitente,
            "to": [destinatario],
            "subject": f"Reclamaron el cupón {numero}",
            "text": contenido,
        }, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Salo/1.0 (+https://salo-cupones.onrender.com)",
            "Idempotency-Key": f"salo-reclamo-{reclamo_id}",
        },
        method="POST",
    )
    try:
        with urlopen(solicitud, timeout=10) as respuesta:
            if respuesta.status not in (200, 201):
                raise OSError(f"Resend respondió con estado {respuesta.status}")
    except HTTPError as error:
        cuerpo_error = error.read(4096)
        tipo = error.headers.get("Content-Type", "desconocido").split(";", 1)[0]
        servidor = error.headers.get("Server", "desconocido")
        try:
            detalle = json.loads(cuerpo_error.decode("utf-8"))
            if isinstance(detalle, dict):
                mensaje = detalle.get("message") or detalle.get("error") or ""
                if isinstance(mensaje, dict):
                    mensaje = mensaje.get("message") or mensaje.get("name") or ""
            else:
                mensaje = detalle if isinstance(detalle, str) else ""
        except (UnicodeError, ValueError):
            mensaje = ""
        if not mensaje and tipo == "text/plain":
            mensaje = cuerpo_error.decode("utf-8", errors="replace")
        mensaje = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[correo]", str(mensaje))
        mensaje = re.sub(r"\bre_[A-Za-z0-9_-]+\b", "[clave]", mensaje)
        if not mensaje:
            mensaje = f"sin detalle (tipo={tipo[:50]}, servidor={servidor[:50]}, bytes={len(cuerpo_error)})"
        raise OSError(f"Resend HTTP {error.code}: {mensaje[:300]}") from None


def enviar_por_smtp(numero):
    """Conserva el envío local con la clave de aplicación de Gmail."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    destinatario = os.getenv("NOTIFY_TO")
    usuario = os.getenv("SMTP_USER") or destinatario
    clave = os.getenv("SMTP_PASSWORD")
    if not all((host, usuario, clave, destinatario)):
        raise ValueError("Falta configurar NOTIFY_TO o SMTP_PASSWORD")

    seguridad = os.getenv("SMTP_SECURITY", "starttls").lower()
    if seguridad not in ("starttls", "ssl"):
        raise ValueError("SMTP_SECURITY debe ser starttls o ssl")
    puerto = int(os.getenv("SMTP_PORT", "465" if seguridad == "ssl" else "587"))

    mensaje = EmailMessage()
    mensaje["From"] = usuario
    mensaje["To"] = destinatario
    mensaje["Subject"] = f"Reclamaron el cupón {numero}"
    mensaje.set_content(
        f"Se reclamó el {NOMBRES_CUPONES[numero - 1]} (cupón {numero}).\n"
        f"{DESCRIPCIONES_CUPONES[numero - 1]}\n"
        "Fecha por definir"
    )

    contexto = ssl.create_default_context()
    if seguridad == "ssl":
        with smtplib.SMTP_SSL(host, puerto, timeout=10, context=contexto) as servidor:
            servidor.login(usuario, clave)
            servidor.send_message(mensaje)
    else:
        with smtplib.SMTP(host, puerto, timeout=10) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(usuario, clave)
            servidor.send_message(mensaje)


def respuesta_json(start_response, estado, datos):
    cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    start_response(estado, [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(cuerpo))),
        ("Cache-Control", "no-store"),
    ])
    return [cuerpo]


def application(environ, start_response):
    ruta = environ.get("PATH_INFO", "/")
    metodo = environ.get("REQUEST_METHOD", "GET")

    if ruta == "/reclamar" and metodo == "POST":
        longitud = int(environ.get("CONTENT_LENGTH") or 0)
        if longitud < 1 or longitud > 100:
            return respuesta_json(start_response, "400 Bad Request", {"mensaje": "Solicitud no válida."})
        datos = parse_qs(environ["wsgi.input"].read(longitud).decode("utf-8"))
        numero_texto = datos.get("cupon", [""])[0]
        if numero_texto not in {str(n) for n in range(1, 7)}:
            return respuesta_json(start_response, "400 Bad Request", {"mensaje": "Cupón no válido."})
        numero = int(numero_texto)
        try:
            reclamo_id = guardar_reclamo(numero, DESCRIPCIONES_CUPONES[numero - 1])
        except (ValueError, psycopg.Error, OSError) as error:
            print(f"No se pudo guardar el reclamo: {error}")
            return respuesta_json(start_response, "503 Service Unavailable", {
                "mensaje": "No se pudo guardar el cupón en la base de datos. Inténtalo de nuevo."
            })

        try:
            enviar_notificacion(numero, reclamo_id)
        except ValueError as error:
            print(f"Configuración de correo: {error}")
            try:
                actualizar_estado_correo(reclamo_id, "fallido")
            except (ValueError, psycopg.Error, OSError) as error_db:
                print(f"No se pudo actualizar el estado del correo: {error_db}")
            return respuesta_json(start_response, "503 Service Unavailable", {
                "mensaje": "Cupón guardado, pero falta configurar el correo para recibir avisos."
            })
        except (OSError, smtplib.SMTPException) as error:
            print(f"No se pudo enviar el correo: {error}")
            try:
                actualizar_estado_correo(reclamo_id, "fallido")
            except (ValueError, psycopg.Error, OSError) as error_db:
                print(f"No se pudo actualizar el estado del correo: {error_db}")
            return respuesta_json(start_response, "502 Bad Gateway", {
                "mensaje": "Cupón guardado, pero no se pudo enviar el aviso. Inténtalo de nuevo."
            })
        try:
            actualizar_estado_correo(reclamo_id, "enviado")
        except (ValueError, psycopg.Error, OSError) as error:
            print(f"Se envió el correo, pero no se pudo actualizar su estado: {error}")
        return respuesta_json(start_response, "200 OK", {
            "mensaje": "¡Cupón reclamado! Se envió el aviso por correo."
        })

    if ruta == "/" and metodo == "GET":
        contenido = '<h1>Bienvenido</h1><a class="boton-circular" href="/segunda">Presiona aquí</a>'
        respuesta = pagina("Inicio", contenido)
        estado = "200 OK"
    elif ruta == "/segunda" and metodo == "GET":
        botones = "".join(
            f'<button class="cupon" type="button" data-cupon="{numero}">Cupón {numero}</button>'
            for numero in range(1, 7)
        )
        contenido = f"""
        <div class="pantalla-cupones">
            <h1>Elige un cupón</h1>
            <div class="cupones">{botones}</div>
            <a class="volver" href="/">Volver al inicio</a>
        </div>
        <dialog id="ventana-cupon" aria-labelledby="titulo-cupon">
            <h2 id="titulo-cupon"></h2>
            <p class="descripcion-cupon" id="descripcion-cupon"></p>
            <p class="fecha-por-definir">Fecha por definir</p>
            <button class="reclamar" id="reclamar" type="button">Reclamar</button>
            <form method="dialog"><button class="cerrar">Cerrar</button></form>
            <p class="mensaje" id="mensaje-cupon" role="status" aria-live="polite"></p>
        </dialog>
        <button class="candado" id="candado" type="button" aria-label="Ver próxima función">🔒</button>
        <span class="aviso-candado" id="aviso-candado" role="status" hidden>Próximamente</span>
        <script>
            const nombres = {json.dumps(NOMBRES_CUPONES, ensure_ascii=False)};
            const descripciones = {json.dumps(DESCRIPCIONES_CUPONES, ensure_ascii=False)};
            const ventana = document.getElementById("ventana-cupon");
            const titulo = document.getElementById("titulo-cupon");
            const descripcion = document.getElementById("descripcion-cupon");
            const reclamar = document.getElementById("reclamar");
            const mensaje = document.getElementById("mensaje-cupon");
            const avisoCandado = document.getElementById("aviso-candado");
            document.getElementById("candado").addEventListener("click", () => {{
                avisoCandado.hidden = !avisoCandado.hidden;
            }});
            let cuponActual = null;
            document.querySelectorAll(".cupon").forEach(boton => {{
                boton.addEventListener("click", () => {{
                    cuponActual = Number(boton.dataset.cupon);
                    titulo.textContent = nombres[cuponActual - 1];
                    descripcion.textContent = descripciones[cuponActual - 1];
                    mensaje.textContent = "";
                    reclamar.disabled = false;
                    ventana.showModal();
                }});
            }});
            reclamar.addEventListener("click", async () => {{
                reclamar.disabled = true;
                mensaje.textContent = "Enviando aviso...";
                try {{
                    const respuesta = await fetch("/reclamar", {{
                        method: "POST",
                        headers: {{"Content-Type": "application/x-www-form-urlencoded"}},
                        body: new URLSearchParams({{cupon: String(cuponActual)}})
                    }});
                    const datos = await respuesta.json();
                    mensaje.textContent = datos.mensaje;
                    if (!respuesta.ok) reclamar.disabled = false;
                }} catch (error) {{
                    mensaje.textContent = "No se pudo conectar con el servidor. Inténtalo de nuevo.";
                    reclamar.disabled = false;
                }}
            }});
        </script>"""
        respuesta = pagina("Segunda página", contenido)
        estado = "200 OK"
    else:
        respuesta = pagina("Página no encontrada", '<h1>Página no encontrada</h1><a class="volver" href="/">Volver al inicio</a>')
        estado = "404 Not Found"

    start_response(estado, [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(respuesta))),
        ("Cache-Control", "no-store"),
    ])
    return [respuesta]


def iniciar_servidor():
    archivo = Path(__file__)
    ultima_modificacion = archivo.stat().st_mtime_ns
    aplicacion_actual = application

    def servir(environ, start_response):
        nonlocal ultima_modificacion, aplicacion_actual
        modificacion = archivo.stat().st_mtime_ns
        if modificacion != ultima_modificacion:
            aplicacion_actual = runpy.run_path(str(archivo))["application"]
            ultima_modificacion = modificacion
            print("Cambios de app.py cargados.")
        return aplicacion_actual(environ, start_response)

    with make_server("localhost", 8000, servir) as servidor:
        print("Abre http://localhost:8000 en tu navegador")
        servidor.serve_forever()


if __name__ == "__main__":
    iniciar_servidor()
