# Grupo Soldador M.A.M — Sistema de Inventario y Cotizaciones

Sistema web en **Django** para taller de soldadura: inventario, clientes y
cotizaciones con precios congelados. Interfaz oscura estilo Vision UI.

## Requisitos
- Python 3.10+

## Instalación

```bash
cd grupo_soldador
python3 -m venv venv            # ya existe en esta copia
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

```bash
python manage.py migrate
python seed_demo.py     # carga admin, empleado y datos de ejemplo
```

Abre http://127.0.0.1:8000 e inicia sesión:

- **admin / admin1234** (superusuario — cámbiala antes de producción)
- **mecanico1 / taller123** (empleado sin permisos de administración)

## Estructura

```
grupo_soldador/
├── config/              # settings.py, urls.py del proyecto
├── taller/              # la app: models.py, admin.py, views.py
├── templates/
│   ├── base.html        # layout oscuro (sidebar + topbar)
│   ├── registration/login.html
│   └── taller/          # dashboard, inventario, cotizaciones
├── manage.py
└── requirements.txt
```

## Modelos

- **Cliente** — nombre, teléfono, email.
- **Producto** — SKU, tipo (pieza/refacción/herramienta/mano de obra), precio, stock + stock mínimo.
- **Cotización** — folio auto (COT-00001), cliente, vehículo/trabajo, estado, autor.
- **DetalleCotizacion** — producto + cantidad + precio congelado al cotizar.

## Flujo de trabajo

1. `/admin/` → captura productos y datos del sistema.
2. `/admin/taller/cotizacion/add/` → nueva cotización con partidas en línea.
3. `/` → dashboard con KPIs; `/inventario/` y `/cotizaciones/` → listas con filtros.
4. `/clientes/` → lista de clientes con buscador y conteo de cotizaciones;
   `/clientes/nuevo/` → formulario de registro.
5. `/usuarios/` → empleados del sistema y `/usuarios/nuevo/` → crear cuentas
   (solo visible para usuarios con rol administrador/staff).
