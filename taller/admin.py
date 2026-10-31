from django.contrib import admin
from .models import Categoria, Cliente, Producto, Cotizacion, DetalleCotizacion, MovimientoStock, VehiculoCliente


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "parent")
    search_fields = ("nombre",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "email", "creado_en")
    search_fields = ("nombre", "telefono", "email")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "precio_unitario", "stock", "alerta_stock")
    list_filter = ("tipo", "activo")
    search_fields = ("codigo", "nombre")
    list_editable = ("precio_unitario", "stock")

    @admin.display(boolean=True, description="Stock bajo")
    def alerta_stock(self, obj):
        return obj.stock_bajo


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ("producto", "delta", "motivo", "creado_por", "creado_en")
    list_filter = ("creado_en",)
    search_fields = ("producto__codigo", "producto__nombre", "motivo")


class DetalleInline(admin.TabularInline):
    model = DetalleCotizacion
    extra = 1
    readonly_fields = ("subtotal",)


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("folio", "cliente", "vehiculo", "estado", "total", "creado_en")
    list_filter = ("estado", "creado_en")
    search_fields = ("folio", "cliente__nombre", "vehiculo")
    readonly_fields = ("folio", "creado_por")
    inlines = [DetalleInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(VehiculoCliente)
class VehiculoClienteAdmin(admin.ModelAdmin):
    list_display = ("cliente", "descripcion", "creado_en")
    search_fields = ("cliente__nombre", "descripcion")
    list_filter = ("creado_en",)
