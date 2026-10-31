# Desplegar en PythonAnywhere

Guía rápida para subir Grupo Soldador M.A.M a PythonAnywhere (funciona igual en cualquier hosting Python).

## 1. En PythonAnywhere (consola Bash)

```bash
git clone https://github.com/alu222410833-pixel/grupo-soldador.git
cd grupo-soldador
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # crea tu usuario admin (admin / tu contraseña)
python seed_demo.py          # datos de ejemplo (opcional)

# collectstatic SIEMPRE con las variables de producción,
# si no el manifiesto de estáticos queda incompleto y las imágenes no cargan
DJANGO_DEBUG=0 DJANGO_SECRET_KEY="x" DJANGO_ALLOWED_HOSTS="tuusuario.pythonanywhere.com" python manage.py collectstatic --noinput
```

## 2. Variables de entorno (en el archivo WSGI de PythonAnywhere)

En la pestaña **Web** → archivo `..._wsgi.py`, arriba del bloque de Django agrega:

```python
import os
os.environ["DJANGO_DEBUG"] = "0"
os.environ["DJANGO_SECRET_KEY"] = "pon-una-clave-larga-y-aleatoria-aqui"
os.environ["DJANGO_ALLOWED_HOSTS"] = "tuusuario.pythonanywhere.com"
os.environ["DJANGO_CSRF_ORIGINS"] = "https://tuusuario.pythonanywhere.com"
```

Y configura el proyecto:

```python
path = '/home/tuusuario/grupo-soldador'
if path not in sys.path:
    sys.path.insert(0, path)
os.chdir(path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 3. Archivos estáticos y fotos (pestaña Web → Static files)

| URL         | Directorio                            |
|-------------|---------------------------------------|
| `/static/`  | `/home/tuusuario/grupo-soldador/staticfiles` |
| `/media/`   | `/home/tuusuario/grupo-soldador/media`       |

**Reload** y listo: `https://tuusuario.pythonanywhere.com`.

## Actualizar después de `git pull`

```bash
cd ~/grupo-soldador && git pull && source venv/bin/activate
python manage.py migrate
DJANGO_DEBUG=0 DJANGO_SECRET_KEY="x" DJANGO_ALLOWED_HOSTS="tuusuario.pythonanywhere.com" python manage.py collectstatic --noinput
```

Y botón **Reload** en la pestaña Web.

## Notas

- La base de datos es `db.sqlite3` (un archivo). Desde **Administración → Respaldar base de datos** los administradores la descargan con un clic.
- En local todo sigue igual: sin variables de entorno corre en modo desarrollo (DEBUG on).
- Genera una SECRET_KEY nueva con: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
