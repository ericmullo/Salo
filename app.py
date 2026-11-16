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
    min-height: 100dvh;
    margin: 0;
    display: grid;
    place-items: center;
    background: radial-gradient(circle at 20% 10%, #67485e, transparent 34%),
                radial-gradient(circle at 85% 90%, #3e516c, transparent 34%),
                #201e29;
    color: #332a2a;
    font-family: Arial, Helvetica, sans-serif;
    text-align: center;
}
.escena { width: 100%; min-height: 100dvh; display: grid; place-items: center; padding: 14px; }
.telefono {
    position: relative;
    width: min(430px, calc(100vw - 28px), calc((100dvh - 28px) * .48));
    aspect-ratio: 9 / 19.5;
    padding: 8px;
    border: 1px solid #9f9da4;
    border-radius: 58px;
    background: linear-gradient(110deg, #35343b, #a6a5aa 8%, #4a4950 17%, #17171b 54%, #77767d 92%, #2b2a30);
    box-shadow: 0 0 0 2px #141318, 0 28px 75px rgba(0, 0, 0, .55),
                inset 0 0 8px rgba(255, 255, 255, .5);
}
.telefono::before, .telefono::after {
    content: "";
    position: absolute;
    width: 4px;
    background: linear-gradient(#77767e, #27262c);
    border-radius: 3px;
}
.telefono::before { height: 66px; left: -5px; top: 22%; }
.telefono::after { height: 79px; right: -5px; top: 27%; }
.pantalla {
    position: relative;
    height: 100%;
    overflow: hidden;
    border-radius: 50px;
    background: radial-gradient(circle at 12% 15%, rgba(255, 255, 255, .9), transparent 35%),
                radial-gradient(circle at 92% 90%, rgba(245, 179, 160, .42), transparent 40%),
                linear-gradient(160deg, #fffaf6, #f7e7e4 58%, #f9e0dd);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .7);
}
.pantalla-bloqueada {
    background: linear-gradient(180deg, rgba(0, 0, 0, .36), transparent 39%, transparent 62%, rgba(0, 0, 0, .48)),
                url('/assets/fondo-bloqueo.jpeg') center center / cover no-repeat;
    color: #fff;
}
.pantalla-bloqueada .barra-estado { color: #fff; }
.pantalla-bloqueada .barra-inferior { background: #fff; }
.pantalla-bloqueada .contenido-pantalla {
    justify-content: flex-start;
    overflow: hidden;
    touch-action: none;
    padding: clamp(87px, 13vh, 124px) 18px 66px;
}
.reloj-bloqueo {
    width: 100%;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: #fff;
    text-shadow: 0 2px 18px rgba(0, 0, 0, .48);
}
.fecha-bloqueo { margin: 0; font-size: clamp(17px, 3vh, 21px); font-weight: 500; }
.hora-bloqueo { margin: 0; font-size: clamp(69px, 12vh, 103px); font-weight: 300; letter-spacing: -.075em; line-height: 1.05; }
.gesto-desbloqueo {
    position: absolute;
    z-index: 2;
    left: 50%;
    bottom: 34px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 7px;
    width: max-content;
    max-width: calc(100% - 30px);
    padding: 12px 10px;
    border: 0;
    background: transparent;
    color: #fff;
    font: 500 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    text-shadow: 0 1px 8px rgba(0, 0, 0, .85);
    cursor: pointer;
    transform: translateX(-50%);
    animation: insinuar-deslizamiento 2.4s ease-in-out infinite;
}
.gesto-desbloqueo svg { width: 20px; height: 20px; stroke: currentColor; stroke-width: 2.5; fill: none; }
.gesto-desbloqueo:focus-visible { outline: 3px solid #fff; outline-offset: 3px; border-radius: 8px; }
.pantalla-bloqueada.desbloqueando .contenido-pantalla,
.pantalla-bloqueada.desbloqueando .gesto-desbloqueo {
    opacity: 0;
    translate: 0 -70px;
    transition: opacity .32s ease, translate .32s ease;
}
@keyframes insinuar-deslizamiento {
    0%, 75%, 100% { margin-bottom: 0; }
    87% { margin-bottom: 9px; }
}
.isla-dinamica {
    position: absolute;
    z-index: 10;
    top: 11px;
    left: 50%;
    width: 118px;
    height: 32px;
    transform: translateX(-50%);
    border-radius: 20px;
    background: #101014;
    box-shadow: 0 1px 2px rgba(255, 255, 255, .18);
}
.isla-dinamica::after {
    content: "";
    position: absolute;
    top: 12px;
    right: 11px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #222b39;
    box-shadow: inset 0 0 0 2px #161b24;
}
.barra-estado {
    position: absolute;
    z-index: 9;
    top: 17px;
    left: 27px;
    right: 26px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #27232a;
    font-size: 14px;
    font-weight: 700;
}
.indicadores { display: flex; align-items: center; gap: 6px; }
.senal { font-size: 11px; letter-spacing: -2px; }
.wifi { font-size: 15px; line-height: 1; }
.bateria { width: 21px; height: 10px; border: 1.5px solid currentColor; border-radius: 3px; position: relative; }
.bateria::before { content: ""; position: absolute; inset: 1px 3px 1px 1px; background: currentColor; border-radius: 1px; }
.bateria::after { content: ""; position: absolute; right: -4px; top: 2px; width: 2px; height: 4px; background: currentColor; border-radius: 0 2px 2px 0; }
.contenido-pantalla {
    height: 100%;
    width: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 82px 24px 62px;
    scrollbar-width: thin;
}
.contenido-pantalla h1 { margin: 0 0 24px; font-size: clamp(27px, 5vw, 35px); }
.barra-inferior {
    position: absolute;
    z-index: 9;
    bottom: 10px;
    left: 50%;
    width: 34%;
    height: 5px;
    transform: translateX(-50%);
    border-radius: 5px;
    background: #29242b;
    pointer-events: none;
}
.volver:focus-visible,
.cupon:focus-visible, .cerrar:focus-visible, .reclamar:focus-visible,
.candado:focus-visible {
    outline: 3px solid #332a2a;
    outline-offset: 5px;
}
.volver { color: #bc2020; font-size: 18px; }
.pantalla-cupones { width: 100%; margin: auto; }
.cupones {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px 14px;
    margin: 18px auto 30px;
    align-items: center;
    justify-items: center;
    perspective: 900px;
}
.cupon {
    width: 100%;
    min-height: 88px;
    padding: 12px;
    border: 1px solid rgba(255, 255, 255, .38);
    border-bottom: 4px solid rgba(0, 0, 0, .22);
    border-radius: 20px;
    color: #fff;
    font: bold 17px Arial, Helvetica, sans-serif;
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
.cupon:nth-child(1) { background: linear-gradient(145deg, #f46a6a, #bd2323); animation-delay: 0s; }
.cupon:nth-child(2) { background: linear-gradient(145deg, #5e91ee, #194595); animation-delay: -.8s; }
.cupon:nth-child(3) { background: linear-gradient(145deg, #59b68f, #176548); animation-delay: -1.6s; }
.cupon:nth-child(4) { background: linear-gradient(145deg, #b484da, #65368e); animation-delay: -2.4s; }
.cupon:nth-child(5) { background: linear-gradient(145deg, #e09a54, #8d3e0e); animation-delay: -3.2s; }
.cupon:nth-child(6) { background: linear-gradient(145deg, #e26da6, #892052); animation-delay: -4s; }
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
.capa-cupon {
    position: absolute;
    z-index: 12;
    inset: 0;
    display: grid;
    place-items: center;
    padding: 62px 16px 46px;
    background: rgba(30, 20, 30, .58);
}
.capa-cupon[hidden] { display: none; }
.tarjeta-cupon {
    width: 100%;
    max-height: 100%;
    overflow-y: auto;
    padding: 30px 18px;
    border-radius: 26px;
    background: #fff;
    box-shadow: 0 18px 50px rgba(0, 0, 0, .28);
    text-align: center;
}
.tarjeta-cupon h2 { margin: 0 0 12px; font-size: clamp(25px, 6vw, 32px); }
.descripcion-cupon {
    margin: 0 0 20px;
    font-size: clamp(18px, 5vw, 22px);
    line-height: 1.4;
    overflow-wrap: anywhere;
}
.fecha-por-definir { margin: 0 0 20px; font-size: 16px; font-weight: bold; }
.candado {
    position: absolute;
    right: 18px;
    bottom: 33px;
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
    position: absolute;
    right: 18px;
    bottom: 98px;
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
    .escena { padding: 6px; }
    .telefono { width: calc(100vw - 12px); height: calc(100dvh - 12px); aspect-ratio: auto; padding: 5px; border-radius: 44px; }
    .pantalla { border-radius: 39px; }
    .contenido-pantalla { padding-inline: 20px; }
}
@media (max-height: 720px) {
    .contenido-pantalla { justify-content: flex-start; }
    .pantalla-inicio { justify-content: center; }
    .cupon { min-height: 74px; }
    .cupones { gap: 14px 12px; }
}
@media (prefers-reduced-motion: reduce) {
    .cupon { animation: none; transition: none; }
    .gesto-desbloqueo { animation: none; }
    .pantalla-bloqueada.desbloqueando .contenido-pantalla,
    .pantalla-bloqueada.desbloqueando .gesto-desbloqueo { transition: none; }
}
"""


def pagina(titulo, contenido, extras=""):
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
    <div class="escena">
        <div class="telefono">
            <div class="pantalla{' pantalla-bloqueada' if titulo == 'Inicio' else ''}">
                <div class="isla-dinamica" aria-hidden="true"></div>
                <div class="barra-estado" aria-hidden="true">
                    <span id="hora-estado">9:41</span>
                    <span class="indicadores"><span class="senal">▂▄▆</span><span class="wifi">◉</span><span class="bateria"></span></span>
                </div>
                <main class="contenido-pantalla{' pantalla-inicio' if titulo == 'Inicio' else ''}">{contenido}</main>
                {extras}
                <div class="barra-inferior" aria-hidden="true"></div>
            </div>
        </div>
    </div>
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

    if ruta == "/assets/fondo-bloqueo.jpeg" and metodo == "GET":
        imagen = (Path(__file__).parent / "assets" / "fondo-bloqueo.jpeg").read_bytes()
        start_response("200 OK", [
            ("Content-Type", "image/jpeg"),
            ("Content-Length", str(len(imagen))),
            ("Cache-Control", "public, max-age=86400"),
        ])
        return [imagen]

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
        contenido = """
            <div class="reloj-bloqueo">
                <p class="fecha-bloqueo" id="fecha-bloqueo"></p>
                <p class="hora-bloqueo" id="hora-bloqueo"></p>
            </div>
            <button class="gesto-desbloqueo" id="desbloquear" type="button" aria-label="Desliza hacia arriba o pulsa para desbloquear">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 15 7-7 7 7"/></svg>
                <span>Desliza hacia arriba para desbloquear</span>
            </button>"""
        extras = """
        <script>
            const pantalla = document.querySelector('.pantalla-bloqueada');
            const reloj = document.getElementById('hora-bloqueo');
            const fecha = document.getElementById('fecha-bloqueo');
            const horaEstado = document.getElementById('hora-estado');
            const boton = document.getElementById('desbloquear');
            function actualizarReloj() {
                const ahora = new Date();
                const hora = new Intl.DateTimeFormat('es-EC', {
                    hour: '2-digit', minute: '2-digit', hour12: false
                }).format(ahora);
                reloj.textContent = hora;
                horaEstado.textContent = hora;
                fecha.textContent = new Intl.DateTimeFormat('es-EC', {
                    weekday: 'long', day: 'numeric', month: 'long'
                }).format(ahora);
            }
            actualizarReloj();
            setInterval(actualizarReloj, 30000);
            let abriendo = false;
            function desbloquear() {
                if (abriendo) return;
                abriendo = true;
                pantalla.classList.add('desbloqueando');
                setTimeout(() => { window.location.assign('/segunda'); }, 320);
            }
            boton.addEventListener('click', desbloquear);
            let inicio = null;
            pantalla.addEventListener('pointerdown', evento => {
                inicio = { x: evento.clientX, y: evento.clientY };
            });
            pantalla.addEventListener('pointerup', evento => {
                if (!inicio) return;
                const desplazamientoY = inicio.y - evento.clientY;
                const desplazamientoX = Math.abs(inicio.x - evento.clientX);
                if (desplazamientoY >= 65 && desplazamientoX < 100) desbloquear();
                inicio = null;
            });
            pantalla.addEventListener('pointercancel', () => { inicio = null; });
        </script>"""
        respuesta = pagina("Inicio", contenido, extras)
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
        </div>"""
        extras = f"""
        <div class="capa-cupon" id="capa-cupon" hidden>
            <section class="tarjeta-cupon" role="dialog" aria-modal="true" aria-labelledby="titulo-cupon">
                <h2 id="titulo-cupon"></h2>
                <p class="descripcion-cupon" id="descripcion-cupon"></p>
                <p class="fecha-por-definir">Fecha por definir</p>
                <button class="reclamar" id="reclamar" type="button">Reclamar</button>
                <button class="cerrar" id="cerrar-cupon" type="button">Cerrar</button>
                <p class="mensaje" id="mensaje-cupon" role="status" aria-live="polite"></p>
            </section>
        </div>
        <button class="candado" id="candado" type="button" aria-label="Ver próxima función">🔒</button>
        <span class="aviso-candado" id="aviso-candado" role="status" hidden>Próximamente</span>
        <script>
            const nombres = {json.dumps(NOMBRES_CUPONES, ensure_ascii=False)};
            const descripciones = {json.dumps(DESCRIPCIONES_CUPONES, ensure_ascii=False)};
            const capa = document.getElementById("capa-cupon");
            const titulo = document.getElementById("titulo-cupon");
            const descripcion = document.getElementById("descripcion-cupon");
            const reclamar = document.getElementById("reclamar");
            const cerrar = document.getElementById("cerrar-cupon");
            const mensaje = document.getElementById("mensaje-cupon");
            const contenidoPantalla = document.querySelector(".contenido-pantalla");
            const candado = document.getElementById("candado");
            const avisoCandado = document.getElementById("aviso-candado");
            candado.addEventListener("click", () => {{
                avisoCandado.hidden = !avisoCandado.hidden;
            }});
            let cuponActual = null;
            let botonOrigen = null;
            function cerrarCupon() {{
                capa.hidden = true;
                contenidoPantalla.inert = false;
                candado.inert = false;
                botonOrigen?.focus();
            }}
            cerrar.addEventListener("click", cerrarCupon);
            capa.addEventListener("click", evento => {{
                if (evento.target === capa) cerrarCupon();
            }});
            capa.addEventListener("keydown", evento => {{
                if (evento.key === "Escape") cerrarCupon();
                if (evento.key === "Tab") {{
                    if (evento.shiftKey && document.activeElement === reclamar) {{
                        evento.preventDefault();
                        cerrar.focus();
                    }} else if (!evento.shiftKey && document.activeElement === cerrar) {{
                        evento.preventDefault();
                        reclamar.focus();
                    }}
                }}
            }});
            document.querySelectorAll(".cupon").forEach(boton => {{
                boton.addEventListener("click", () => {{
                    botonOrigen = boton;
                    cuponActual = Number(boton.dataset.cupon);
                    titulo.textContent = nombres[cuponActual - 1];
                    descripcion.textContent = descripciones[cuponActual - 1];
                    mensaje.textContent = "";
                    reclamar.disabled = false;
                    avisoCandado.hidden = true;
                    capa.hidden = false;
                    contenidoPantalla.inert = true;
                    candado.inert = true;
                    reclamar.focus();
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
        respuesta = pagina("Segunda página", contenido, extras)
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
