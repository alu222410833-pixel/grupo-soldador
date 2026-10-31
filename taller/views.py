from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Count
from django.utils import timezone
from .models import Cliente, Cotizacion, Producto


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
def inventario(request):
    tipo = request.GET.get("tipo", "")
    qs = Producto.objects.all()
    if tipo:
        qs = qs.filter(tipo=tipo)
    return render(request, "taller/inventario.html", {
        "productos": qs[:200],
        "tipos": Producto.Tipo.choices,
        "tipo_actual": tipo,
    })
