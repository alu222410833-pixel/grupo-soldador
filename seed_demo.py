"""Datos de demostración. Uso: python seed_demo.py"""
import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from taller.models import Cliente, Producto, Cotizacion, DetalleCotizacion

admin, _ = User.objects.get_or_create(
    username="admin",
    defaults={"is_superuser": True, "is_staff": True,
              "first_name": "Carlos", "last_name": "Pérez"},
)
admin.set_password("admin1234")
admin.is_superuser = admin.is_staff = True
admin.save()

u, created = User.objects.get_or_create(
    username="mecanico1", defaults={"first_name": "Luis", "last_name": "Hernández"}
)
if created:
    u.set_password("taller123")
    u.save()

c1, _ = Cliente.objects.get_or_create(nombre="Juan Pérez García", defaults={"telefono": "555-0101"})
c2, _ = Cliente.objects.get_or_create(nombre="María López Ruiz", defaults={"telefono": "555-0102"})
c3, _ = Cliente.objects.get_or_create(nombre="Carlos Méndez")

Producto.objects.get_or_create(
    codigo="ELC-7018",
    defaults={"nombre": 'Electrodo 7018 1/8"', "tipo": "REFACCION",
              "precio_unitario": Decimal("18.50"), "stock": 200, "stock_minimo": 50},
)
Producto.objects.get_or_create(
    codigo="DISC-14",
    defaults={"nombre": 'Disco de corte 14"', "tipo": "HERRAMIENTA",
              "precio_unitario": Decimal("85.00"), "stock": 2, "stock_minimo": 5},
)
Producto.objects.get_or_create(
    codigo="MO-SOLD",
    defaults={"nombre": "Mano de obra soldadura (hora)", "tipo": "MANO_OBRA",
              "precio_unitario": Decimal("350.00"), "stock": 0},
)
mo = Producto.objects.get(codigo="MO-SOLD")
disco = Producto.objects.get(codigo="DISC-14")

cot, _ = Cotizacion.objects.get_or_create(
    folio="COT-00001",
    defaults={"cliente": c1, "vehiculo": "Nissan Sentra 2018",
              "estado": "APROBADA", "creado_por": admin},
)
if not cot.detalles.exists():
    DetalleCotizacion.objects.create(cotizacion=cot, producto=mo, cantidad=8)
    DetalleCotizacion.objects.create(cotizacion=cot, producto=disco, cantidad=4)

cot2, _ = Cotizacion.objects.get_or_create(
    folio="COT-00002",
    defaults={"cliente": c2, "vehiculo": "Chevrolet Aveo 2016",
              "estado": "PENDIENTE", "creado_por": admin},
)
if not cot2.detalles.exists():
    DetalleCotizacion.objects.create(cotizacion=cot2, producto=mo, cantidad=6)

cot3, _ = Cotizacion.objects.get_or_create(
    folio="COT-00003",
    defaults={"cliente": c3, "vehiculo": "Ford Figo 2019",
              "estado": "EN_PROCESO", "creado_por": admin},
)
if not cot3.detalles.exists():
    DetalleCotizacion.objects.create(cotizacion=cot3, producto=mo, cantidad=13)
    DetalleCotizacion.objects.create(cotizacion=cot3, producto=disco, cantidad=2)

print("Demo lista — admin/admin1234 · mecanico1/taller123")
