"""Entrada para Gunicorn en Render."""

from app import application
from database import preparar_base_datos


preparar_base_datos()
