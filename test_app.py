"""Pruebas del reclamo sin enviar correos reales."""

from io import BytesIO
import json
import os
import unittest
from unittest.mock import patch

import app
import database


def solicitar(ruta, metodo="GET", datos=b""):
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
    resultado["cuerpo"] = b"".join(app.application(entorno, iniciar))
    return resultado


class AplicacionTest(unittest.TestCase):
    def test_pagina_tiene_seis_cupones_y_reclamar(self):
        pagina = solicitar("/segunda")
        html = pagina["cuerpo"].decode("utf-8")
        self.assertEqual(pagina["estado"], "200 OK")
        self.assertEqual(html.count("data-cupon="), 6)
        self.assertIn('id="reclamar"', html)
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
        self.assertEqual(solicitud.get_header("Idempotency-key"), "salo-reclamo-42")

    def test_neon_usa_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://ejemplo"}, clear=True):
            with patch.object(database.psycopg, "connect") as conectar:
                database.conectar()
        self.assertEqual(conectar.call_args.args, ("postgresql://ejemplo",))


if __name__ == "__main__":
    unittest.main()
