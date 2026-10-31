import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Count, Q
from django.http import JsonResponse
from django.utils import timezone
from .models import Categoria, Cliente, Cotizacion, DetalleCotizacion, MovimientoStock, Producto, VehiculoCliente


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
    q = request.GET.get("q", "").strip()
    qs = Cotizacion.objects.select_related("cliente").prefetch_related("detalles")
    if estado:
        qs = qs.filter(estado=estado)
    if q:
        qs = qs.filter(
            Q(folio__icontains=q)
            | Q(cliente__nombre__icontains=q)
            | Q(cliente__apellido_paterno__icontains=q)
            | Q(cliente__apellido_materno__icontains=q)
            | Q(vehiculo__icontains=q)
        )
    return render(request, "taller/cotizaciones.html", {
        "cotizaciones": qs[:100],
        "estados": Cotizacion.Estado.choices,
        "estado_actual": estado,
        "q": q,
    })


@login_required
def cotizacion_detalle(request, pk):
    cot = get_object_or_404(
        Cotizacion.objects.select_related("cliente", "creado_por")
        .prefetch_related("detalles__producto"),
        pk=pk,
    )
    return render(request, "taller/cotizacion_detalle.html", {"cot": cot})


@login_required
def clientes(request):
    qs = (
        Cliente.objects.annotate(num_cotizaciones=Count("cotizaciones"))
        .order_by("-creado_en")
    )
    buscar = request.GET.get("q", "").strip()
    if buscar:
        qs = qs.filter(
            Q(nombre__icontains=buscar)
            | Q(apellido_paterno__icontains=buscar)
            | Q(apellido_materno__icontains=buscar)
            | Q(telefono__icontains=buscar)
        )
    return render(request, "taller/clientes.html", {
        "clientes": qs[:200],
        "buscar": buscar,
    })


@login_required
def cliente_nuevo(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if nombre:
            tel = request.POST.get("telefono", "").strip()
            if tel and not tel.startswith("+52"):
                tel = "+52 " + tel
            cliente = Cliente.objects.create(
                nombre=nombre,
                apellido_paterno=request.POST.get("apellido_paterno", "").strip(),
                apellido_materno=request.POST.get("apellido_materno", "").strip(),
                telefono=tel,
                email=request.POST.get("email", "").strip(),
                direccion=request.POST.get("direccion", "").strip(),
            )
            n_veh = 0
            i = 0
            while True:
                desc = request.POST.get(f"veh_desc_{i}")
                if desc is None:
                    break
                img = request.FILES.get(f"veh_img_{i}") or request.FILES.get(f"veh_cam_{i}")
                if desc.strip() or img:
                    VehiculoCliente.objects.create(cliente=cliente, descripcion=desc.strip(), imagen=img)
                    n_veh += 1
                i += 1
            extra = f" ({n_veh} vehículo{'s' if n_veh != 1 else ''})" if n_veh else ""
            messages.success(request, f"Cliente {cliente.nombre_completo} registrado{extra}.")
            return redirect("clientes")
        messages.error(request, "El nombre del cliente es obligatorio.")
    return render(request, "taller/cliente_form.html")


@login_required
def cliente_nueva(request):
    """Alta rápida de cliente desde la cotización (JSON)."""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido."}, status=405)
    nombre = request.POST.get("nombre", "").strip()
    if not nombre:
        return JsonResponse({"error": "El nombre es obligatorio."}, status=400)
    paterno = request.POST.get("apellido_paterno", "").strip()
    materno = request.POST.get("apellido_materno", "").strip()
    tel = request.POST.get("telefono", "").strip()
    if tel and not tel.startswith("+52"):
        tel = "+52 " + tel
    existe = Cliente.objects.filter(
        nombre__iexact=nombre, apellido_paterno__iexact=paterno, apellido_materno__iexact=materno
    ).first()
    if existe:
        return JsonResponse({"id": existe.pk, "nombre": existe.nombre_completo, "tel": existe.telefono, "existe": True})
    c = Cliente.objects.create(
        nombre=nombre, apellido_paterno=paterno, apellido_materno=materno, telefono=tel
    )
    return JsonResponse({"id": c.pk, "nombre": c.nombre_completo, "tel": c.telefono})


@login_required
@user_passes_test(lambda u: u.is_staff)
def usuarios(request):
    User = get_user_model()
    return render(request, "taller/usuarios.html", {
        "empleados": User.objects.order_by("username"),
    })


@login_required
def cliente_detalle(request, pk):
    c = get_object_or_404(Cliente.objects.prefetch_related("vehiculos", "cotizaciones"), pk=pk)
    return render(request, "taller/cliente_detalle.html", {
        "c": c,
        "cotizaciones": c.cotizaciones.order_by("-creado_en")[:50],
        "vehiculos": c.vehiculos.all(),
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
        for pid, cant, ldesc, lprecio in zip(
            request.POST.getlist("producto"), request.POST.getlist("cantidad"),
            request.POST.getlist("libre_desc"), request.POST.getlist("libre_precio"),
        ):
            producto = Producto.objects.filter(pk=pid or 0).first()
            if not (cant.isdigit() and int(cant) > 0):
                continue
            if producto:
                detalles.append({"producto": producto, "cantidad": int(cant)})
            elif ldesc.strip():
                try:
                    precio = Decimal(lprecio)
                except (InvalidOperation, TypeError):
                    precio = None
                if precio is not None and precio >= 0:
                    detalles.append({"descripcion": ldesc.strip(), "precio": precio,
                                     "cantidad": int(cant)})

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
            for d in detalles:
                DetalleCotizacion.objects.create(
                    cotizacion=cot,
                    producto=d.get("producto"),
                    descripcion=d.get("descripcion", ""),
                    cantidad=d["cantidad"],
                    precio_unitario=d.get("precio"),
                )
            messages.success(request, f"Cotización {cot.folio} creada — ${cot.total:,.2f} MXN.")
            return redirect("cotizaciones")

    clientes_qs = list(Cliente.objects.prefetch_related("vehiculos"))
    clientes_map = [
        {"id": c.pk, "nombre": c.nombre_completo, "tel": c.telefono,
         "vehs": [{"desc": v.descripcion, "img": v.imagen.url if v.imagen else ""}
                  for v in c.vehiculos.all()]}
        for c in clientes_qs
    ]
    productos_map = [
        {"id": p.pk, "codigo": p.codigo, "nombre": p.nombre,
         "tipo": p.tipo, "tipo_label": p.get_tipo_display(),
         "precio": float(p.precio_unitario)}
        for p in Producto.objects.filter(activo=True)
    ]
    return render(request, "taller/cotizacion_form.html", {
        "estados": Cotizacion.Estado.choices,
        "clientes_map": clientes_map,
        "productos_map": productos_map,
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

        tipo = request.POST.get("tipo") or Producto.Tipo.PIEZA
        if not codigo or not nombre:
            messages.error(request, "Código y nombre son obligatorios.")
        elif precio is None or precio < 0:
            messages.error(request, "Ingresa un precio válido.")
        elif tipo == Producto.Tipo.MANO_OBRA:
            messages.error(request, "La mano de obra se registra desde la sección Servicios.")
        elif Producto.objects.filter(codigo=codigo).exists():
            messages.error(request, f"El código {codigo} ya existe en el inventario.")
        else:
            stock = request.POST.get("stock", "0")
            stock_min = request.POST.get("stock_minimo", "3")
            Producto.objects.create(
                codigo=codigo,
                nombre=nombre,
                tipo=tipo,
                categoria=Categoria.objects.filter(pk=request.POST.get("categoria") or 0).first(),
                precio_unitario=precio,
                stock=int(stock) if stock.isdigit() else 0,
                stock_minimo=int(stock_min) if stock_min.isdigit() else 3,
                imagen=request.FILES.get("imagen") or request.FILES.get("imagen_camara"),
            )
            messages.success(request, f"Producto {codigo} registrado.")
            return redirect("inventario")

    tipos_fisicos = [t for t in Producto.Tipo.choices if t[0] != Producto.Tipo.MANO_OBRA]
    tipo_inicial = request.GET.get("tipo", "")
    return render(request, "taller/producto_form.html", {
        "tipos": tipos_fisicos,
        "tipo_inicial": tipo_inicial if tipo_inicial in dict(tipos_fisicos) else "",
        "codigos_siguientes": _codigos_siguientes(),
        "categorias_flat": [{"id": c.pk, "label": str(c)} for c in Categoria.objects.select_related("parent")],
    })


_PREFIJOS_TIPO = {
    Producto.Tipo.PIEZA: "PIE",
    Producto.Tipo.REFACCION: "REF",
    Producto.Tipo.HERRAMIENTA: "HER",
    Producto.Tipo.MANO_OBRA: "SER",
}


def _codigos_siguientes():
    """Prochain code libre par type : PIE-N, REF-N, HER-N (max suffixe numérique + 1)."""
    res = {}
    for tipo, prefijo in _PREFIJOS_TIPO.items():
        maximo = 0
        for codigo in Producto.objects.filter(codigo__startswith=prefijo + "-").values_list("codigo", flat=True):
            m = re.match(rf"^{prefijo}-(\d+)$", codigo)
            if m:
                maximo = max(maximo, int(m.group(1)))
        res[tipo] = f"{prefijo}-{maximo + 1}"
    return res


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
def categoria_nueva(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée."}, status=405)
    nombre = request.POST.get("nombre", "").strip()
    if not nombre:
        return JsonResponse({"error": "El nombre es obligatorio."}, status=400)
    parent = Categoria.objects.filter(pk=request.POST.get("parent") or 0).first()
    existe = Categoria.objects.filter(nombre__iexact=nombre, parent=parent).first()
    if existe:
        return JsonResponse({"id": existe.pk, "label": str(existe), "existe": True})
    cat = Categoria.objects.create(nombre=nombre, parent=parent)
    return JsonResponse({"id": cat.pk, "label": str(cat)})


@login_required
def inventario(request):
    tipo = request.GET.get("tipo", "")
    buscar = request.GET.get("q", "").strip()
    qs = Producto.objects.select_related("categoria").exclude(tipo=Producto.Tipo.MANO_OBRA)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if buscar:
        qs = qs.filter(
            Q(codigo__icontains=buscar)
            | Q(nombre__icontains=buscar)
            | Q(categoria__nombre__icontains=buscar)
        )
    orden = request.GET.get("sort", "")
    dire = request.GET.get("dir", "asc")
    SORTS = {
        "codigo": "codigo", "nombre": "nombre", "categoria": "categoria__nombre",
        "tipo": "tipo", "precio": "precio_unitario", "stock": "stock", "estado": "activo",
    }
    if orden in SORTS:
        qs = qs.order_by(("-" if dire == "desc" else "") + SORTS[orden], "codigo")
    pagina = Paginator(qs, 15).get_page(request.GET.get("page") or 1)
    productos = list(pagina.object_list)
    params_base = urlencode({k: v for k, v in [("tipo", tipo), ("q", buscar)] if v})
    params = params_base + ("&" if params_base else "") + urlencode({"sort": orden, "dir": dire}) if orden else params_base
    return render(request, "taller/inventario.html", {
        "productos": productos,
        "pagina": pagina,
        "params": params,
        "params_base": params_base,
        "buscar": buscar,
        "orden": orden,
        "dire": dire,
        "hay_fotos": any(p.imagen for p in productos),
        "tipos": [(v, l) for v, l in Producto.Tipo.choices if v != Producto.Tipo.MANO_OBRA],
        "tipo_actual": tipo,
    })


@login_required
def producto_detalle(request, pk):
    p = get_object_or_404(Producto.objects.select_related("categoria"), pk=pk)
    lineas = (
        DetalleCotizacion.objects.filter(producto=p)
        .select_related("cotizacion", "cotizacion__cliente")
        .order_by("-cotizacion__creado_en")[:50]
    )
    return render(request, "taller/producto_detalle.html", {
        "p": p,
        "lineas": lineas,
        "movimientos": p.movimientos.select_related("creado_por")[:50],
    })


@login_required
def producto_ajustar(request, pk):
    p = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        try:
            delta = int(request.POST.get("delta", ""))
        except ValueError:
            delta = 0
        motivo = request.POST.get("motivo", "").strip()
        if delta == 0:
            messages.error(request, "El ajuste no puede ser 0.")
        elif p.tipo == Producto.Tipo.MANO_OBRA:
            messages.error(request, "La mano de obra no lleva stock.")
        elif p.stock + delta < 0:
            messages.error(request, f"Stock insuficiente: hay {p.stock}, no se pueden sacar {-delta}.")
        else:
            MovimientoStock.objects.create(
                producto=p, delta=delta, motivo=motivo, creado_por=request.user
            )
            Producto.objects.filter(pk=p.pk).update(stock=p.stock + delta)
            messages.success(request, f"Stock de {p.codigo}: {p.stock} → {p.stock + delta} ({delta:+d}).")
    return redirect("producto_detalle", pk=pk)


@login_required
def producto_toggle(request, pk):
    p = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        p.activo = not p.activo
        p.save(update_fields=["activo"])
        messages.success(request, f"{p.codigo} {'activado' if p.activo else 'desactivado'}.")
    return redirect("producto_detalle", pk=pk)


@login_required
def producto_editar(request, pk):
    p = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        try:
            precio = Decimal(request.POST.get("precio_unitario", ""))
        except InvalidOperation:
            precio = None
        if not nombre:
            messages.error(request, "El nombre es obligatorio.")
        elif precio is None or precio < 0:
            messages.error(request, "Ingresa un precio válido.")
        else:
            p.nombre = nombre
            p.descripcion = request.POST.get("descripcion", "").strip()
            p.categoria = Categoria.objects.filter(pk=request.POST.get("categoria") or 0).first()
            p.precio_unitario = precio
            sm = request.POST.get("stock_minimo", "")
            p.stock_minimo = int(sm) if sm.isdigit() else p.stock_minimo
            img = request.FILES.get("imagen") or request.FILES.get("imagen_camara")
            if img:
                p.imagen = img
            p.save()
            messages.success(request, f"Producto {p.codigo} actualizado.")
            return redirect("producto_detalle", pk=pk)
    return render(request, "taller/producto_editar.html", {
        "p": p,
        "categorias_flat": [{"id": c.pk, "label": str(c)} for c in Categoria.objects.select_related("parent")],
    })


@login_required
def servicios(request):
    buscar = request.GET.get("q", "").strip()
    qs = Producto.objects.filter(tipo=Producto.Tipo.MANO_OBRA)
    if buscar:
        qs = qs.filter(
            Q(codigo__icontains=buscar)
            | Q(nombre__icontains=buscar)
            | Q(descripcion__icontains=buscar)
        )
    pagina = Paginator(qs, 15).get_page(request.GET.get("page") or 1)
    params = urlencode({"q": buscar}) if buscar else ""
    return render(request, "taller/servicios.html", {
        "servicios": pagina.object_list,
        "pagina": pagina,
        "params": params,
        "buscar": buscar,
    })


@login_required
def servicio_nuevo(request):
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
            messages.error(request, f"El código {codigo} ya existe.")
        else:
            incluye = [i.strip() for i in request.POST.getlist("incluye") if i.strip()]
            descripcion = request.POST.get("descripcion", "").strip()
            if incluye:
                descripcion = (descripcion + "\n" if descripcion else "") + "\n".join("• " + i for i in incluye)
            Producto.objects.create(
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                tipo=Producto.Tipo.MANO_OBRA,
                precio_unitario=precio,
                stock=0,
                stock_minimo=0,
            )
            messages.success(request, f"Servicio {codigo} registrado.")
            return redirect("servicios")

    return render(request, "taller/servicio_form.html", {
        "codigo_sugerido": _codigos_siguientes()[Producto.Tipo.MANO_OBRA],
    })
