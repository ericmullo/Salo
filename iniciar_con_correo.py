"""Pide la clave de aplicación de Gmail sin mostrarla ni guardarla."""

from getpass import getpass
import os

from app import iniciar_servidor


if __name__ == "__main__":
    if not os.getenv("SMTP_PASSWORD"):
        clave = getpass("Clave de aplicación de Gmail (no se mostrará): ").replace(" ", "")
        if not clave:
            raise SystemExit("No se ingresó la clave de aplicación.")
        os.environ["SMTP_PASSWORD"] = clave
    iniciar_servidor()
