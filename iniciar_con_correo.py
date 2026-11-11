"""Inicia PostgreSQL y Gmail sin guardar las contraseñas en archivos."""

from getpass import getpass
import os

from app import iniciar_servidor
from database import preparar_base_datos


if __name__ == "__main__":
    if not os.getenv("NOTIFY_TO"):
        destinatario = input("Correo que recibirá los avisos: ").strip()
        if not destinatario:
            raise SystemExit("No se ingresó un correo destinatario.")
        os.environ["NOTIFY_TO"] = destinatario

    if not os.getenv("DB_PASSWORD") and not os.getenv("DATABASE_URL"):
        clave_db = getpass("Contraseña de PostgreSQL (no se mostrará): ")
        if not clave_db:
            raise SystemExit("No se ingresó la contraseña de PostgreSQL.")
        os.environ["DB_PASSWORD"] = clave_db

    preparar_base_datos()
    print("Base de datos y tabla reclamos listas.")

    if not os.getenv("SMTP_PASSWORD"):
        clave = getpass("Clave de aplicación de Gmail (no se mostrará): ").replace(" ", "")
        if not clave:
            raise SystemExit("No se ingresó la clave de aplicación.")
        os.environ["SMTP_PASSWORD"] = clave
    iniciar_servidor()
