"""Pruebas del reclamo sin enviar correos reales."""

from io import BytesIO
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import app
import database


def solicitar(ruta, metodo="GET", datos=b"", cabeceras=None):
    resultado = {}

    def iniciar(estado, cabeceras):
        resultado["estado"] = estado
        resultado["cabeceras"] = dict(cabeceras)

    entorno = {
        "PATH_INFO": ruta,
        "REQUEST_METHOD": metodo,
        "CONTENT_LENGTH": str(len(datos)),
        "wsgi.input": BytesIO(datos),
    }
    entorno.update(cabeceras or {})
    resultado["cuerpo"] = b"".join(app.application(entorno, iniciar))
    return resultado


class AplicacionTest(unittest.TestCase):
    def test_aviso_visita_solo_desde_la_pantalla_propia(self):
        with patch.object(app, "enviar_aviso_visita") as enviar:
            inicio = solicitar("/")
            prohibido = solicitar("/aviso-visita", "POST", cabeceras={
                "HTTP_ORIGIN": "https://otra-pagina.test", "HTTP_HOST": "salo-cupones.onrender.com"
            })
            permitido = solicitar("/aviso-visita", "POST", cabeceras={
                "HTTP_ORIGIN": "https://salo-cupones.onrender.com", "HTTP_HOST": "salo-cupones.onrender.com"
            })
        self.assertIn("fetch('/aviso-visita'", inicio["cuerpo"].decode("utf-8"))
        self.assertEqual(prohibido["estado"], "403 Forbidden")
        self.assertEqual(permitido["estado"], "204 No Content")
        enviar.assert_called_once_with()

    def test_aviso_visita_usa_correo_configurado(self):
        with patch.dict(os.environ, {"RESEND_API_KEY": "clave-de-prueba", "NOTIFY_TO": "destino@ejemplo.test"}, clear=True):
            with patch.object(app, "urlopen") as abrir:
                abrir.return_value.__enter__.return_value.status = 200
                app.enviar_aviso_visita()
        solicitud = abrir.call_args.args[0]
        datos = json.loads(solicitud.data)
        self.assertEqual(datos["to"], ["destino@ejemplo.test"])
        self.assertEqual(datos["subject"], "Alguien entró a Salo")
        self.assertIn("pantalla de bloqueo", datos["text"])
        self.assertTrue(solicitud.get_header("Idempotency-key").startswith("salo-visita-"))

    def test_inicio_muestra_bloqueo_y_foto(self):
        inicio = solicitar("/")
        html = inicio["cuerpo"].decode("utf-8")
        foto = solicitar("/assets/fondo-bloqueo.jpeg")
        self.assertEqual(inicio["estado"], "200 OK")
        self.assertIn('id="hora-bloqueo"', html)
        self.assertIn("Desliza hacia arriba para desbloquear", html)
        self.assertNotIn('class="boton-circular"', html)
        self.assertEqual(foto["estado"], "200 OK")
        self.assertEqual(foto["cabeceras"]["Content-Type"], "image/jpeg")
        self.assertTrue(foto["cuerpo"].startswith(b"\xff\xd8"))

    def test_desbloqueo_muestra_tres_apps_y_notas_editables(self):
        escritorio = solicitar("/segunda")
        html = escritorio["cuerpo"].decode("utf-8")
        self.assertEqual(escritorio["estado"], "200 OK")
        for ruta in ("/spotify", "/notas", "/salo"):
            self.assertIn(f'href="{ruta}"', html)
        self.assertNotIn('>Chat</span>', html)
        self.assertNotIn("Elige un cupón", html)
        spotify = solicitar("/spotify")["cuerpo"].decode("utf-8")
        self.assertIn("El Malo", spotify)
        self.assertIn("Aventura", spotify)
        self.assertIn("https://open.spotify.com/embed/track/1lE7XktMlmV4V5kPv9xXIm", spotify)
        self.assertIn("Bonita", spotify)
        self.assertIn("Cabas", spotify)
        self.assertIn("https://open.spotify.com/embed/track/04oLwA0vDrMi2XN6hVTVSC", spotify)
        self.assertEqual(spotify.count('class="reproductor-spotify"'), 2)
        self.assertIn('allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"', spotify)
        notas = solicitar("/notas")["cuerpo"].decode("utf-8")
        self.assertIn('<textarea class="nota-texto"', notas)
        self.assertIn("localStorage.setItem('salo-nota'", notas)
        carta = solicitar("/salo")
        self.assertEqual(carta["estado"], "200 OK")
        self.assertIn("Hola Salo, lo que hace el tiempo libre.", carta["cuerpo"].decode("utf-8"))
        self.assertIn("no cambies flaca eres perfecta", carta["cuerpo"].decode("utf-8"))

    def test_pagina_tiene_seis_cupones_y_reclamar(self):
        pagina = solicitar("/cupones")
        html = pagina["cuerpo"].decode("utf-8")
        self.assertEqual(pagina["estado"], "200 OK")
        self.assertEqual(html.count("data-cupon="), 6)
        self.assertIn('id="reclamar"', html)
        self.assertIn("Fecha por definir", html)
        self.assertNotIn('type="date"', html)
        self.assertIn('id="candado"', html)
        self.assertIn("Próximamente", html)
        for descripcion in app.DESCRIPCIONES_CUPONES:
            self.assertIn(descripcion, html)

    def test_reclamo_invalido_no_envia_correo(self):
        with patch.object(app, "guardar_reclamo") as guardar, patch.object(app, "enviar_notificacion") as enviar:
            resultado = solicitar("/reclamar", "POST", b"cupon=7")
        self.assertEqual(resultado["estado"], "400 Bad Request")
        guardar.assert_not_called()
        enviar.assert_not_called()

    def test_reclamo_valido_envia_aviso(self):
        with patch.object(app, "guardar_reclamo", return_value=42) as guardar:
            with patch.object(app, "enviar_notificacion") as enviar:
                with patch.object(app, "actualizar_estado_correo") as actualizar:
                    resultado = solicitar("/reclamar", "POST", b"cupon=3")
        self.assertEqual(resultado["estado"], "200 OK")
        self.assertIn("Se envió", json.loads(resultado["cuerpo"])["mensaje"])
        self.assertNotIn("PostgreSQL", json.loads(resultado["cuerpo"])["mensaje"])
        guardar.assert_called_once_with(3, app.DESCRIPCIONES_CUPONES[2])
        enviar.assert_called_once_with(3, 42)
        actualizar.assert_called_once_with(42, "enviado")

    def test_sin_clave_no_confirma_reclamo(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(app, "guardar_reclamo", return_value=42):
                with patch.object(app, "actualizar_estado_correo") as actualizar:
                    resultado = solicitar("/reclamar", "POST", b"cupon=1")
        self.assertEqual(resultado["estado"], "503 Service Unavailable")
        self.assertIn("falta configurar", json.loads(resultado["cuerpo"])["mensaje"])
        actualizar.assert_called_once_with(42, "fallido")

    def test_correo_contiene_cupon_y_destinatario(self):
        variables = {
            "SMTP_HOST": "smtp.ejemplo.test",
            "SMTP_USER": "remitente@ejemplo.test",
            "SMTP_PASSWORD": "clave-de-prueba",
            "NOTIFY_TO": "destino@ejemplo.test",
        }
        with patch.dict("os.environ", variables, clear=True):
            with patch.object(app.smtplib, "SMTP") as smtp:
                app.enviar_notificacion(2, 42)
        mensaje = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        self.assertEqual(mensaje["To"], "destino@ejemplo.test")
        self.assertIn("cupón 2", mensaje["Subject"])
        self.assertIn("Segundo cupón", mensaje.get_content())
        self.assertIn(app.DESCRIPCIONES_CUPONES[1], mensaje.get_content())
        self.assertIn("Fecha por definir", mensaje.get_content())
        self.assertEqual(smtp.call_args.args, ("smtp.ejemplo.test", 587))
        smtp.return_value.__enter__.return_value.starttls.assert_called_once()

    def test_resend_envia_correo_por_https(self):
        with patch.dict(os.environ, {"RESEND_API_KEY": "clave-de-prueba", "NOTIFY_TO": "destino@ejemplo.test"}, clear=True):
            with patch.object(app, "urlopen") as abrir:
                abrir.return_value.__enter__.return_value.status = 200
                app.enviar_notificacion(1, 42)
        solicitud = abrir.call_args.args[0]
        datos = json.loads(solicitud.data)
        self.assertEqual(solicitud.full_url, "https://api.resend.com/emails")
        self.assertEqual(datos["to"], ["destino@ejemplo.test"])
        self.assertIn(app.DESCRIPCIONES_CUPONES[0], datos["text"])
        self.assertIn("Fecha por definir", datos["text"])
        self.assertEqual(solicitud.get_header("Idempotency-key"), "salo-reclamo-42")
        self.assertEqual(solicitud.get_header("User-agent"), "Salo/1.0 (+https://salo-cupones.onrender.com)")
        self.assertEqual(solicitud.get_header("Accept"), "application/json")

    def test_resend_registra_motivo_sin_exponer_correo_ni_clave(self):
        cuerpo = json.dumps({"error": {"message": "Solo se puede enviar a destino@ejemplo.test con re_clave123456"}}).encode()
        respuesta = HTTPError("https://api.resend.com/emails", 403, "Forbidden", {}, BytesIO(cuerpo))
        with patch.dict(os.environ, {"RESEND_API_KEY": "re_clave123456", "NOTIFY_TO": "destino@ejemplo.test"}, clear=True):
            with patch.object(app, "urlopen", side_effect=respuesta):
                with self.assertRaises(OSError) as fallo:
                    app.enviar_notificacion(1, 42)
        self.assertIn("Resend HTTP 403", str(fallo.exception))
        self.assertIn("[correo]", str(fallo.exception))
        self.assertIn("[clave]", str(fallo.exception))
        self.assertNotIn("destino@ejemplo.test", str(fallo.exception))
        self.assertNotIn("re_clave123456", str(fallo.exception))

    def test_resend_registra_metadatos_si_no_hay_mensaje(self):
        respuesta = HTTPError("https://api.resend.com/emails", 403, "Forbidden", {"Content-Type": "text/html", "Server": "cloudflare"}, BytesIO(b"<html>Forbidden</html>"))
        with patch.dict(os.environ, {"RESEND_API_KEY": "clave-de-prueba", "NOTIFY_TO": "destino@ejemplo.test"}, clear=True):
            with patch.object(app, "urlopen", side_effect=respuesta):
                with self.assertRaises(OSError) as fallo:
                    app.enviar_notificacion(1, 42)
        self.assertIn("tipo=text/html", str(fallo.exception))
        self.assertIn("servidor=cloudflare", str(fallo.exception))

    def test_neon_usa_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://ejemplo"}, clear=True):
            with patch.object(database.psycopg, "connect") as conectar:
                database.conectar()
        self.assertEqual(conectar.call_args.args, ("postgresql://ejemplo",))


if __name__ == "__main__":
    unittest.main()
