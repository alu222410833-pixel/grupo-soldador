from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("inventario/", views.inventario, name="inventario"),
    path("inventario/nuevo/", views.producto_nuevo, name="producto_nuevo"),
    path("inventario/<int:pk>/", views.producto_detalle, name="producto_detalle"),
    path("inventario/<int:pk>/editar/", views.producto_editar, name="producto_editar"),
    path("inventario/<int:pk>/ajustar/", views.producto_ajustar, name="producto_ajustar"),
    path("inventario/<int:pk>/activo/", views.producto_toggle, name="producto_toggle"),
    path("servicios/", views.servicios, name="servicios"),
    path("servicios/nuevo/", views.servicio_nuevo, name="servicio_nuevo"),
    path("cotizaciones/", views.cotizaciones, name="cotizaciones"),
    path("cotizaciones/nueva/", views.cotizacion_nueva, name="cotizacion_nueva"),
    path("clientes/", views.clientes, name="clientes"),
    path("clientes/nuevo/", views.cliente_nuevo, name="cliente_nuevo"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nuevo/", views.usuario_nuevo, name="usuario_nuevo"),
    path("administracion/", views.administracion, name="administracion"),
    path("administracion/categorias/", views.categorias, name="categorias"),
    path("categorias/nueva/", views.categoria_nueva, name="categoria_nueva"),
]
