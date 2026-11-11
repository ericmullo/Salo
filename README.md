# Cupones en Python

La página y la API se sirven desde el mismo proceso Python. En producción, un servicio web de Render sirve ambas y Neon almacena los reclamos.

## Iniciar la aplicación

La aplicación usa PostgreSQL y el controlador Psycopg. En PowerShell, desde esta carpeta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe iniciar_con_correo.py
```

El inicio solicitará el correo destinatario, la contraseña de PostgreSQL y la clave de aplicación de Gmail. Las contraseñas no se muestran ni se guardan en archivos. Si ya están definidas las variables `NOTIFY_TO`, `DB_PASSWORD` y `SMTP_PASSWORD`, no volverá a pedirlas. Detén antes cualquier servidor anterior en el puerto 8000 con `Ctrl+C`.

Abre http://localhost:8000 en el navegador. El botón rojo circular lleva a la segunda página. Allí hay seis cupones que se adaptan a pantallas pequeñas.

## PostgreSQL

El programa se conecta a PostgreSQL local con el usuario `postgres` y la base `Salo`. Si la base o la tabla `reclamos` no existen, las crea al iniciar. Cada reclamo guarda el número y la descripción del cupón, la fecha y el estado del correo (`pendiente`, `enviado` o `fallido`). El reclamo se guarda antes de enviar el aviso. La conexión local fue verificada con la base `Salo` y la tabla `reclamos`.

Para ver los registros en pgAdmin, abre la herramienta de consultas de `Salo` y ejecuta:

```sql
SELECT id, cupon_numero, descripcion, reclamado_en, correo_estado
FROM public.reclamos
ORDER BY id DESC;
```

Puedes cambiar la conexión mediante `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. La contraseña no está escrita en el proyecto.

En producción, `DATABASE_URL` tiene prioridad sobre esas variables locales. El inicio en Render crea la tabla `reclamos` dentro de la base indicada por esa URL; no intenta crear otra base de datos en Neon.

## Correo

Dentro de cada cupón, **Reclamar** envía un aviso a la dirección configurada en `NOTIFY_TO`. En local, el remitente es la misma cuenta de Gmail, salvo que configures `SMTP_USER`. Para crear la clave de aplicación de Gmail:

1. Activa la verificación en dos pasos de Google y crea una **clave de aplicación** en https://myaccount.google.com/apppasswords.
2. Pégala cuando `iniciar_con_correo.py` la solicite.
3. Abre http://localhost:8000/segunda y reclama un cupón.

Después de iniciar esta versión, los cambios posteriores en `app.py` se cargarán al recargar el navegador. Para cambiar de una versión anterior a esta, detén primero el servidor anterior con `Ctrl+C`.

La configuración de Gmail ya está preparada (`smtp.gmail.com`, puerto 587, STARTTLS). Si más adelante usas otro proveedor, puedes cambiarla mediante estas variables de entorno:

| Variable | Uso |
| --- | --- |
| `SMTP_HOST` | Servidor SMTP; por defecto `smtp.gmail.com` |
| `SMTP_PORT` | Puerto; por defecto 587 con STARTTLS o 465 con SSL |
| `SMTP_SECURITY` | `starttls` (predeterminado) o `ssl` |
| `SMTP_USER` | Remitente; por defecto, el mismo valor de `NOTIFY_TO` |
| `SMTP_PASSWORD` | Contraseña o clave de aplicación del remitente |
| `NOTIFY_TO` | Destinatario de los avisos |

Si falla el correo, el reclamo permanece en PostgreSQL con estado `fallido` y la pantalla mostrará el error.

## Despliegue en Render y Neon

El archivo `render.yaml` prepara un servicio web gratuito con Gunicorn. Para publicarlo:

1. Crea un proyecto en Neon. En **Connect**, copia la URL de conexión **directa** (sin `-pooler`), que incluye los parámetros de seguridad TLS.
2. Registra una cuenta en Resend con el mismo correo que pondrás en `NOTIFY_TO` y crea una clave API. El remitente de prueba `onboarding@resend.dev` permite enviar avisos a la dirección de esa misma cuenta. Para enviar a otras direcciones, necesitarás un dominio verificado y cambiar `RESEND_FROM`.
3. Sube este proyecto a GitHub, sin contraseñas ni claves en los archivos.
4. En Render, crea un **Blueprint** desde ese repositorio. Render leerá `render.yaml` y pedirá `DATABASE_URL` (la URL de Neon), `RESEND_API_KEY` (la clave de Resend) y `NOTIFY_TO` (tu correo). Pega cada valor en su campo de Render.
5. Cuando el despliegue termine, abre la dirección `onrender.com` del servicio y reclama un cupón. La misma dirección sirve la página y el backend.

Render gratuito bloquea SMTP en los puertos de Gmail; por eso, si existe `RESEND_API_KEY`, el backend envía los avisos por la API HTTPS de Resend. El Gmail SMTP local sigue disponible cuando no se configura Resend.
