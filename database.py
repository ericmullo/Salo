"""Conexión y operaciones de reclamos en PostgreSQL."""

import os

import psycopg
from psycopg import sql


def configuracion(nombre_base=None):
    clave = os.getenv("DB_PASSWORD")
    if not clave:
        raise ValueError("Falta configurar DB_PASSWORD")
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": nombre_base or os.getenv("DB_NAME", "Salo"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": clave,
        "connect_timeout": 5,
    }


def conectar(nombre_base=None, autocommit=False):
    url = os.getenv("DATABASE_URL")
    if url:
        if nombre_base:
            raise ValueError("No se puede cambiar la base indicada por DATABASE_URL")
        return psycopg.connect(url, connect_timeout=10, autocommit=autocommit)
    return psycopg.connect(**configuracion(nombre_base), autocommit=autocommit)


def preparar_base_datos():
    """Crea la base y la tabla si todavía no existen."""
    if not os.getenv("DATABASE_URL"):
        nombre = os.getenv("DB_NAME", "Salo")
        with conectar("postgres", autocommit=True) as conexion:
            existe = conexion.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (nombre,)
            ).fetchone()
            if not existe:
                conexion.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))

    with conectar() as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS reclamos (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                cupon_numero SMALLINT NOT NULL CHECK (cupon_numero BETWEEN 1 AND 6),
                descripcion TEXT NOT NULL,
                fecha_cupon DATE,
                reclamado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                correo_estado TEXT NOT NULL DEFAULT 'pendiente'
                    CHECK (correo_estado IN ('pendiente', 'enviado', 'fallido'))
            )
        """)
        conexion.execute("ALTER TABLE reclamos ADD COLUMN IF NOT EXISTS fecha_cupon DATE")


def guardar_reclamo(numero, descripcion, fecha_cupon):
    with conectar() as conexion:
        fila = conexion.execute(
            "INSERT INTO reclamos (cupon_numero, descripcion, fecha_cupon) VALUES (%s, %s, %s) RETURNING id",
            (numero, descripcion, fecha_cupon),
        ).fetchone()
        return fila[0]


def actualizar_estado_correo(reclamo_id, estado):
    if estado not in ("enviado", "fallido"):
        raise ValueError("Estado de correo no válido")
    with conectar() as conexion:
        conexion.execute(
            "UPDATE reclamos SET correo_estado = %s WHERE id = %s",
            (estado, reclamo_id),
        )
