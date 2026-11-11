# Pantalla inicial en Python

Para usar los cupones sin activar el correo, ejecuta:

```powershell
python app.py
```

Abre http://localhost:8000 en el navegador. El botón rojo circular de la primera pantalla lleva a la segunda página. Allí hay seis botones de colores; cada uno abre su cupón en una ventana dentro de la página. La distribución se adapta a pantallas pequeñas.

Dentro de cada cupón, **Reclamar** envía un aviso desde y hacia `ericrodrigomullo@gmail.com`. Para activar el correo:

1. Activa la verificación en dos pasos de Google y crea una **clave de aplicación** en https://myaccount.google.com/apppasswords.
2. Detén cualquier servidor anterior con `Ctrl+C`.
3. Ejecuta `python iniciar_con_correo.py`.
4. Pega la clave de aplicación cuando se solicite. No se mostrará ni quedará guardada en el proyecto.
5. Abre http://localhost:8000/segunda y reclama un cupón.

Después de iniciar esta versión, los cambios posteriores en `app.py` se cargarán al recargar el navegador. Para cambiar de una versión anterior a esta, detén primero el servidor anterior con `Ctrl+C`.

La configuración de Gmail ya está preparada (`smtp.gmail.com`, puerto 587, STARTTLS). Si más adelante usas otro proveedor, puedes cambiarla mediante estas variables de entorno:

| Variable | Uso |
| --- | --- |
| `SMTP_HOST` | Servidor SMTP; por defecto `smtp.gmail.com` |
| `SMTP_PORT` | Puerto; por defecto 587 con STARTTLS o 465 con SSL |
| `SMTP_SECURITY` | `starttls` (predeterminado) o `ssl` |
| `SMTP_USER` | Remitente; por defecto `ericrodrigomullo@gmail.com` |
| `SMTP_PASSWORD` | Contraseña o clave de aplicación del remitente |
| `NOTIFY_TO` | Destinatario; por defecto `ericrodrigomullo@gmail.com` |

No guardes la contraseña en los archivos del proyecto. Si falta la configuración o falla el envío, la pantalla mostrará un mensaje y no confirmará el reclamo.

La aplicación usa únicamente la biblioteca estándar de Python.
