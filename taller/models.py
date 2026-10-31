from django.db import models
from django.conf import settings


class Cliente(models.Model):
    nombre = models.CharField("nombre(s)", max_length=150)
    apellido_paterno = models.CharField(max_length=100, blank=True)
    apellido_materno = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    @property
    def nombre_completo(self):
        return " ".join(p for p in (self.nombre, self.apellido_paterno, self.apellido_materno) if p)

    def __str__(self):
        return self.nombre_completo


class VehiculoCliente(models.Model):
    """Vehículo del cliente — puede tener varios, cada uno con foto."""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="vehiculos")
    descripcion = models.CharField(max_length=200, blank=True,
        help_text="Ej. Nissan Tsuru 2015 rojo, placas ABC-123")
    imagen = models.ImageField(upload_to="vehiculos/", blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"

    def __str__(self):
        return self.descripcion or f"Vehículo de {self.cliente}"


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE,
        null=True, blank=True, related_name="subcategorias",
        verbose_name="categoría padre",
    )

    class Meta:
        ordering = ["parent__nombre", "nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        if self.parent:
            return f"{self.parent.nombre} › {self.nombre}"
        return self.nombre


class Producto(models.Model):
    class Tipo(models.TextChoices):
        PIEZA = "PIEZA", "Pieza"
        REFACCION = "REFACCION", "Refacción"
        HERRAMIENTA = "HERRAMIENTA", "Herramienta"
        MANO_OBRA = "MANO_OBRA", "Mano de obra"

    codigo = models.CharField("SKU / código", max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="productos",
        verbose_name="categoría",
    )
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.PIEZA)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=3)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Producto / Servicio"
        verbose_name_plural = "Productos y Servicios"

    @property
    def stock_bajo(self):
        # La mano de obra no lleva stock físico
        return self.tipo != self.Tipo.MANO_OBRA and self.stock <= self.stock_minimo

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class MovimientoStock(models.Model):
    """Entrada/salida de inventario — el stock nunca se edita a mano, se ajusta."""

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="movimientos")
    delta = models.IntegerField(help_text="+ entrada, − salida")
    motivo = models.CharField(max_length=200, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="movimientos_stock",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Movimiento de stock"
        verbose_name_plural = "Movimientos de stock"

    def __str__(self):
        signo = "+" if self.delta >= 0 else ""
        return f"{signo}{self.delta} × {self.producto.codigo}"


class Cotizacion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        EN_PROCESO = "EN_PROCESO", "En proceso"

    folio = models.CharField(max_length=20, unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="cotizaciones")
    vehiculo = models.CharField("vehículo / trabajo", max_length=150,
                                help_text='Ej. "Nissan Sentra 2018" o "Portón herrería"')
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.BORRADOR)
    notas = models.TextField(blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"

    @property
    def total(self):
        return sum(d.subtotal for d in self.detalles.all())

    def save(self, *args, **kwargs):
        if not self.folio:
            super().save(*args, **kwargs)
            self.folio = f"COT-{self.pk:05d}"
            return super().save(update_fields=["folio"])
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} — {self.cliente}"


class DetalleCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Precio congelado al momento de cotizar"
    )

    class Meta:
        verbose_name = "Detalle de cotización"
        verbose_name_plural = "Detalles de cotización"

    @property
    def subtotal(self):
        if self.precio_unitario is None:
            return None
        return self.cantidad * self.precio_unitario

    def save(self, *args, **kwargs):
        if self.precio_unitario is None:
            self.precio_unitario = self.producto.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} × {self.producto.nombre}"
