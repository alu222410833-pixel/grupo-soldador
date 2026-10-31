from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Count
from django.utils import timezone
from .models import Categoria, Cliente, Cotizacion, DetalleCotizacion, Producto


@login_required
def dashboard(request):
    hoy = timezone.localdate()

    cotizaciones_hoy = Cotizacion.objects.filter(creado_en__date=hoy)
    total_hoy = cotizaciones_hoy.annotate(
        sub=ExpressionWrapper(
            F("detalles__cantidad") * F("detalles__precio_unitario"),
            output_field=DecimalField(),
        )
    ).aggregate(t=Sum("sub"))["t"] or 0

    recientes = (
        Cotizacion.objects.select_related("cliente")
        .prefetch_related("detalles")[:5]
    )

    context = {
        "cotizaciones_dia": cotizaciones_hoy.count(),
        "total_dia": total_hoy,
        "pendientes": Cotizacion.objects.filter(estado=Cotizacion.Estado.PENDIENTE).count(),
        "stock_bajo": sum(1 for p in Producto.objects.filter(activo=True) if p.stock_bajo),
        "recientes": recientes,
    }
    return render(request, "taller/dashboard.html", context)


@login_required
def cotizaciones(request):
    estado = request.GET.get("estado", "")
    qs = Cotizacion.objects.select_related("cliente").prefetch_related("detalles")
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, "taller/cotizaciones.html", {
        "cotizaciones": qs[:100],
        "estados": Cotizacion.Estado.choices,
        "estado_actual": estado,
    })


@login_required
def clientes(request):
    qs = (
        Cliente.objects.annotate(num_cotizaciones=Count("cotizaciones"))
        .order_by("-creado_en")
    )
    buscar = request.GET.get("q", "").strip()
    if buscar:
        qs = qs.filter(nombre__icontains=buscar)
    return render(request, "taller/clientes.html", {
        "clientes": qs[:200],
        "buscar": buscar,
    })


@login_required
def cliente_nuevo(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if nombre:
            cliente = Cliente.objects.create(
                nombre=nombre,
                telefono=request.POST.get("telefono", "").strip(),
                email=request.POST.get("email", "").strip(),
                direccion=request.POST.get("direccion", "").strip(),
            )
            messages.success(request, f"Cliente {cliente.nombre} registrado.")
            return redirect("clientes")
        messages.error(request, "El nombre del cliente es obligatorio.")
    return render(request, "taller/cliente_form.html")


@login_required
@user_passes_test(lambda u: u.is_staff)
def usuarios(request):
    User = get_user_model()
    return render(request, "taller/usuarios.html", {
        "empleados": User.objects.order_by("username"),
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def usuario_nuevo(request):
    User = get_user_model()
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        if username and password:
            if User.objects.filter(username=username).exists():
                messages.error(request, f"El usuario {username} ya existe.")
            else:
                User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=request.POST.get("first_name", "").strip(),
                    last_name=request.POST.get("last_name", "").strip(),
                    is_staff=bool(request.POST.get("es_admin")),
                )
                messages.success(request, f"Empleado {username} creado.")
                return redirect("usuarios")
        else:
            messages.error(request, "Usuario y contraseña son obligatorios.")
    return render(request, "taller/usuario_form.html")


@login_required
def cotizacion_nueva(request):
    if request.method == "POST":
        cliente = Cliente.objects.filter(pk=request.POST.get("cliente") or 0).first()
        vehiculo = request.POST.get("vehiculo", "").strip()
        estado = request.POST.get("estado", "")
        if estado not in Cotizacion.Estado.values:
            estado = Cotizacion.Estado.BORRADOR

        detalles = []
        for pid, cant in zip(request.POST.getlist("producto"), request.POST.getlist("cantidad")):
            producto = Producto.objects.filter(pk=pid or 0).first()
            if producto and cant.isdigit() and int(cant) > 0:
                detalles.append((producto, int(cant)))

        if not cliente:
            messages.error(request, "Selecciona un cliente.")
        elif not vehiculo:
            messages.error(request, "Describe el vehículo o trabajo a cotizar.")
        elif not detalles:
            messages.error(request, "Agrega al menos una partida con producto y cantidad válidos.")
        else:
            cot = Cotizacion.objects.create(
                cliente=cliente,
                vehiculo=vehiculo,
                estado=estado,
                notas=request.POST.get("notas", "").strip(),
                creado_por=request.user,
            )
            for producto, cant in detalles:
                DetalleCotizacion.objects.create(
                    cotizacion=cot, producto=producto, cantidad=cant
                )
            messages.success(request, f"Cotización {cot.folio} creada — ${cot.total:,.2f} MXN.")
            return redirect("cotizaciones")

    return render(request, "taller/cotizacion_form.html", {
        "clientes": Cliente.objects.all(),
        "productos": Producto.objects.filter(activo=True),
        "estados": Cotizacion.Estado.choices,
    })


@login_required
def producto_nuevo(request):
    if request.method == "POST":
        codigo = request.POST.get("codigo", "").strip().upper()
        nombre = request.POST.get("nombre", "").strip()
        try:
            precio = Decimal(request.POST.get("precio_unitario", ""))
        except InvalidOperation:
            precio = None

        if not codigo or not nombre:
            messages.error(request, "Código y nombre son obligatorios.")
        elif precio is None or precio < 0:
            messages.error(request, "Ingresa un precio válido.")
        elif Producto.objects.filter(codigo=codigo).exists():
            messages.error(request, f"El código {codigo} ya existe en el inventario.")
        else:
            stock = request.POST.get("stock", "0")
            stock_min = request.POST.get("stock_minimo", "3")
            tipo = request.POST.get("tipo") or Producto.Tipo.PIEZA
            Producto.objects.create(
                codigo=codigo,
                nombre=nombre,
                tipo=tipo,
                categoria=Categoria.objects.filter(pk=request.POST.get("categoria") or 0).first(),
                precio_unitario=precio,
                stock=int(stock) if stock.isdigit() else 0,
                stock_minimo=int(stock_min) if stock_min.isdigit() else 3,
                imagen=request.FILES.get("imagen"),
            )
            messages.success(request, f"Producto {codigo} registrado.")
            return redirect("servicios" if tipo == Producto.Tipo.MANO_OBRA else "inventario")

    tipo_inicial = request.GET.get("tipo", "")
    return render(request, "taller/producto_form.html", {
        "tipos": Producto.Tipo.choices,
        "tipo_inicial": tipo_inicial if tipo_inicial in Producto.Tipo.values else "",
        "categorias": Categoria.objects.prefetch_related("subcategorias").filter(parent__isnull=True),
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def administracion(request):
    User = get_user_model()
    return render(request, "taller/administracion.html", {
        "num_productos": Producto.objects.count(),
        "num_clientes": Cliente.objects.count(),
        "num_cotizaciones": Cotizacion.objects.count(),
        "num_usuarios": User.objects.count(),
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def categorias(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if nombre:
            Categoria.objects.create(
                nombre=nombre,
                parent=Categoria.objects.filter(pk=request.POST.get("parent") or 0).first(),
            )
            messages.success(request, f"Categoría {nombre} creada.")
            return redirect("categorias")
        messages.error(request, "El nombre de la categoría es obligatorio.")
    return render(request, "taller/categorias.html", {
        "categorias": Categoria.objects.prefetch_related("subcategorias", "productos")
                                       .filter(parent__isnull=True),
    })


@login_required
def inventario(request):
    tipo = request.GET.get("tipo", "")
    qs = Producto.objects.select_related("categoria").exclude(tipo=Producto.Tipo.MANO_OBRA)
    if tipo:
        qs = qs.filter(tipo=tipo)
    return render(request, "taller/inventario.html", {
        "productos": qs[:200],
        "tipos": [(v, l) for v, l in Producto.Tipo.choices if v != Producto.Tipo.MANO_OBRA],
        "tipo_actual": tipo,
    })


@login_required
def servicios(request):
    return render(request, "taller/servicios.html", {
        "servicios": Producto.objects.filter(tipo=Producto.Tipo.MANO_OBRA)[:200],
    })
