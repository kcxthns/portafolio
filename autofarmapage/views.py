from django.shortcuts import redirect, render
from autofarmapage.forms import LoginForm
from autofarmapage.forms import RegistrarForm
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as do_logout
from .models import Region, Comuna, CentroSalud, TipoEmpleado, Persona
from .connbd import ConexionBD
import cx_Oracle
from autofarmapage.forms import EditarForm
from autofarmapage.models import Caducado, Componente, Medicamento, MedidaComponente, Receta, RegistroInformes, StockMedicamento, TipoComponente, TipoMedicamento, TipoTratamiento, TutorPaciente, Usuario
from django.contrib import messages
from autofarmapage.managers import UserManager
from django.core.mail import send_mail
from django.core.paginator import Paginator
from .validacion import Validador
from datetime import datetime

# Create your views here.


def index(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)

        # datos para autenticar al usuario
        username = request.POST['rut']
        password = request.POST['password']

        # se autentica el usuario
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            # print(type(user.rut.rut))
            # revisa el tipo de empleado que se conecta y lo redirije a su respectivo home
            if user.id_tipo_empleado == TipoEmpleado.objects.filter(id_tipo_empleado="3").get():
                # página del administrador
                return redirect('homeadmi')
            elif user.id_tipo_empleado == TipoEmpleado.objects.filter(id_tipo_empleado='2').get():
                # página del colaborador de farmacia
                return redirect('homefarma')
            elif user.id_tipo_empleado == TipoEmpleado.objects.filter(id_tipo_empleado='1').get():
                return redirect('home_medico')
        else:
            messages.error(
                request, 'Tu nombre de usuario o contraseña no son correctos.')

    return render(request, 'autofarmapage/index.html', {})


def homeadmi(request):
    return render(request, 'autofarmapage/homeadmi.html', {})


def agregarusuario(request):
    # Querys para poblar los select del formulario de creación de persona
    #regiones = Region.objects.all()
    regiones = Region.objects.get(
        id_region=request.user.rut.id_comuna.id_region.id_region)
    #ciudades = Comuna.objects.all().order_by('nombre_comuna')
    ciudades = Comuna.objects.get(
        id_comuna=request.user.rut.id_comuna.id_comuna)
    #centro_salud = CentroSalud.objects.all().order_by('id_comuna')
    centro_salud = CentroSalud.objects.get(
        id_centro=request.user.rut.id_centro.id_centro)
    tipo_empleado = TipoEmpleado.objects.all()

    if request.method == 'POST':
        rut = request.POST['rut']
        #dv = request.POST['dv']
        rut = rut.replace('.', '')
        rut = rut.replace('-', '')
        rut = rut[0 : len(rut) - 1]
        nombres = request.POST['nombres']
        app_paterno = request.POST['apellido_paterno']
        app_materno = request.POST['apellido_materno']
        telefono = int(request.POST['telefono'])
        email = request.POST['correo_electronico']
        direccion = request.POST['direccion']
        comuna = int(request.user.rut.id_comuna.id_comuna)
        centro_s = int(request.user.rut.id_centro.id_centro)
        id_tipo_empleado = int(request.POST['id_tipo_empleado'])
        rut_tutor = None

        print(rut)
        # conexión a la bd
        bd = ConexionBD()
        conn = bd.conectar()
        cursor = conn.cursor()
        realizado = cursor.var(int)

        # Llamado al procedimiento almacenado para crear persona (no crea usuario)
        cursor.callproc('pkg_crear_usuario.sp_crear_persona', [
                        rut, nombres, app_paterno, app_materno, telefono, email, direccion, comuna, centro_s, rut_tutor, realizado])
        print(realizado.getvalue())

        if int(realizado.getvalue()) == 1:
            # mensaje exito
            #messages.success(request, 'Datos Agregados al Sistema.')
            usuario = Usuario.objects.create_user(rut, id_tipo_empleado)

            # inserta el rut en la tabla de medicos o de colaboradores de farmacia
            if id_tipo_empleado == 1:
                cursor.callproc(
                    'pkg_crear_usuario.sp_ingresar_medico', [rut])
            if id_tipo_empleado == 2:
                cursor.callproc(
                    'pkg_crear_usuario.sp_ingresar_col_farmacia', [rut])

            #new_usuario = Usuario.objects.filter(rut=rut)
            mensaje_email = 'Tu usuario es ' + \
                usuario.rut.rut + ' .Tu contraseña es ' + rut[0:4]

            # envío de mail con el usuario y la contraseña
            send_mail(
                'Bienvenido a Autofarma.',
                mensaje_email,
                'torpedo.page@gmail.com',
                [email],
                fail_silently=False
                )
            return redirect('exito-crear-usuario')
        elif int(realizado.getvalue()) == 0:
            # mesaje error
            messages.error(
                request, 'Se ha producido un problema y los datos no han sido almacenados. Por Favor intente nuevamente.')

    return render(request, 'autofarmapage/agregar-usuario.html', {'regiones': regiones, 'ciudades': ciudades, 'centro_salud': centro_salud, 'tipo_empleado': tipo_empleado})


def guardadoUsuarioExito(request):
    return render(request, 'autofarmapage/exito-guardar-usuario.html', {})


def guardadoTutorExito(request):
    return render(request, 'autofarmapage/exito-guardar-tutor.html', {})


def listarusuario(request):
    person = Persona.objects.filter(
        id_centro=request.user.rut.id_centro).order_by('rut')

    if request.method == 'GET':
        criterio_busqueda = request.GET.get('q')
        submitBtn = request.GET.get('submit')
        if criterio_busqueda is not None:
            person = Persona.objects.filter(id_centro=request.user.rut.id_centro).filter(
                rut=criterio_busqueda).order_by('rut')
            paginador = Paginator(person, 20)
            pagina = request.GET.get('page')
            person = paginador.get_page(pagina)
            data5 = {
                'person': person,
            }
            parametros = request.GET.copy()

            if 'page' in parametros:
                del parametros['page']

            datos['parametros'] = parametros
            return render(request, 'autofarmapage/listar-usuario.html', data5)

    if request.method == 'POST':
        rut_tutor = request.POST['rutTutor']
        rut_paciente = request.POST['rutPaciente']
        # conexión a la bd
        bd = ConexionBD()
        con = bd.conectar()
        cursor = con.cursor()
        realizado = cursor.var(int)
        # procedimiento de creación del tutor
        cursor.callproc('pkg_crear_usuario.sp_crear_tutor', [
                        rut_tutor, rut_paciente, realizado])
        # print(realizado.getvalue())
        if realizado.getvalue() == 1:
            return redirect('exito-guardar-tutor')

    paginador = Paginator(person, 20)
    pagina = request.GET.get('page')
    person = paginador.get_page(pagina)

    data5 = {
        'person': person,
    }
    return render(request, 'autofarmapage/listar-usuario.html', data5)


def listarinforme(request):
    informe = RegistroInformes.objects.all()
    datainfo = {
        'informe': informe
    }
    return render(request, 'autofarmapage/listar-informe.html', datainfo)


def modificarUsuarioExito(request):
    return render(request, 'autofarmapage/exito-modificar-usuario.html', {})


def editarPersona(request, rut):
    persona = Persona.objects.filter(rut=rut)
    tutor = TutorPaciente.objects.all()
    ciudades = Comuna.objects.all().order_by('nombre_comuna')
    centro_salud = CentroSalud.objects.all().order_by('id_comuna')
    dataPerson = {
        'persona': persona,
        'tutor': tutor,
        'ciudades': ciudades,
        'centro_salud': centro_salud
    }

    if request.method == 'POST':
        rut = request.POST['rut']
        nombres = request.POST['nombres']
        app_paterno = request.POST['apellido_paterno']
        app_materno = request.POST['apellido_materno']
        telefono = int(request.POST['telefono'])
        email = request.POST['correo_electronico']
        direccion = request.POST['direccion']
        comuna = int(request.POST['id_comuna'])
        centro_s = int(request.POST['id_centro'])
        rut_tutor = request.POST['rut_tutor']
        # lo hice para probar :(
        sql = ('update persona '
               'set nombres = :nombres '
               'where rut = :rut')
        bd = ConexionBD()

        try:
            # establecer nueva conexion
            with cx_Oracle.connect(bd.bd_user,
                                   bd.bd_password,
                                   bd.dsn,
                                   encoding="UTF-8") as connection:
                # crear cursor
                with connection.cursor() as cursor:
                    # ejecutar el procedimiento
                    realizado = cursor.var(int)
                    cursor.callproc('pkg_administrar_usuario.sp_editar_persona', [
                                    rut, nombres, app_paterno, app_materno, telefono, email, direccion, comuna, centro_s, rut_tutor, realizado])

                    if int(realizado.getvalue()) == 1:
                        return redirect('exito-modificar-usuario')
                    elif int(realizado.getvalue()) == 0:
                        messages.error(
                            request, 'Se ha producido algún error, por favor intente nuevamente.')
                # commit los cambios
                    connection.commit()
        except cx_Oracle.Error as error:
            print(error)

    return render(request, 'autofarmapage/editaruser.html', dataPerson)


def deshabilitarUsuario(request, rut):
    persona = Persona.objects.filter(rut=rut)
    if request.method == 'POST':
        rut_usuario = request.POST['rutUsuario']
        opcion = int(request.POST['opcion'])
        bd = ConexionBD()
        conn = bd.conectar()
        cursor = conn.cursor()
        realizado = cursor.var(int)
        cursor.callproc('pkg_administrar_usuario.sp_des_habilitar_user', [
                        rut_usuario, opcion, realizado])
        print(realizado.getvalue())
        if int(realizado.getvalue()) == 1 and opcion == 1:
            messages.success(request, 'Usuario ' +
                             rut_usuario + ' habilitado exitosamente')
        elif int(realizado.getvalue()) == 1 and opcion == 0:
            messages.success(request, 'Usuario ' +
                             rut_usuario + ' deshabilitado exitosamente')
        elif int(realizado.getvalue()) == 0:
            messages.error(
                request, 'Ha ocurrido un error al procesar los datos, por favor intenta nuevamente.')
    data = {
        'persona': persona
    }
    return render(request, 'autofarmapage/deshabilitarpage.html', data)


def passwordResetCompleto(request):
    return render(request, 'registration/password_reset_complete_custom.html', {})


def logout(request):
    do_logout(request)
    return redirect('/')

# vistas gestion farmacia


def homeFarmacia(request):
    # establece el codigo de medicamento, que se guarda en la sesión del usuario
    request.session['codigo_medicamento'] = 0
    return render(request, 'autofarmapage/homefarma.html', {})


def agregarMedicamento(request):
    tipoMedicamento = TipoMedicamento.objects.all()
    # resetea el codigo de medicamento a cero si ya ha sido usado durante la sesión del usuario
    request.session['codigo_medicamento'] = 0

    if request.method == 'POST':
        nombreMedi = request.POST['nombre_medicamento']
        descripcionMedi = request.POST['descripcion']
        fabricanteMedi = request.POST['fabricante']
        idTipoMedi = int(request.POST['id_tipo_med'])
        # conexión a bd
        bd = ConexionBD()
        con = bd.conectar()
        cursor = con.cursor()

        realizado = cursor.var(int)
        codigoMedi = cursor.var(int)
        cursor.callproc('pkg_administrar_medicamento.sp_ingresar_medicamento', [
                        nombreMedi, descripcionMedi, fabricanteMedi, idTipoMedi, realizado, codigoMedi])

        if realizado.getvalue() == 1:
            print(codigoMedi.getvalue())
            # guarda el valor de el codigo de medicamento generado en el PL/SQL en la sesión del usuario, esta se guarda en la bd encriptado
            request.session['codigo_medicamento'] = codigoMedi.getvalue()
            new_stock = cursor.var(int)

            cursor.callproc('pkg_administrar_medicamento.sp_crear_stock_medi', [
                            request.session['codigo_medicamento'], request.user.rut.rut, new_stock])
            print(new_stock)
            return redirect('agregar-componente')
        elif realizado.getvalue() == 0:
            messages.error(
                request, 'Se ha producido un error al guardar los datos, por favor intente nuevamente')

    return render(request, 'autofarmapage/agregar-medicamento.html', {'tipoMedicamento': tipoMedicamento})


def agregarComponente(request):
    medidaComponente = MedidaComponente.objects.all()
    tipoComponente = TipoComponente.objects.all()
    medicamento = Medicamento.objects.get(
        codigo=request.session['codigo_medicamento'])

    componentes = Componente.objects.all().filter(codigo=medicamento.codigo)

    if request.method == 'POST':
        _id_componente = request.POST.get('id_componente')
        # borra el componente si se ha presionado la opción de borrar
        if _id_componente is not None:
            delete_comp = Componente.objects.get(id_componente=_id_componente)
            delete_comp.delete()
        else:
            # añade el componente si se ha seleccionado añadir en el formulario
            nombreComp = request.POST['nombre_componente']
            medida = request.POST['medida_componente']
            idMedida = int(request.POST['id_medida_componente'])
            idTipoComp = int(request.POST['id_tipo_componente'])
            codMedicamento = int(request.session['codigo_medicamento'])

            bd = ConexionBD()
            con = bd.conectar()
            cursor = con.cursor()

            realizado = cursor.var(int)

            cursor.callproc('pkg_administrar_medicamento.sp_add_componente', [
                            codMedicamento, nombreComp, medida, idTipoComp, idMedida, realizado])

    # print(request.session['codigo_medicamento'])

    datos = {
        'medidaComponente': medidaComponente,
        'tipoComponente': tipoComponente,
        'componentes': componentes,
        'medicamento': medicamento
    }

    return render(request, 'autofarmapage/agregar-componente.html', datos)


def guardadoMedicamentoExito(request):
    return render(request, 'autofarmapage/exito-guardar-medicamento.html', {})


def listarMedicamento(request):
    medicamentos = Medicamento.objects.all()
    stock = StockMedicamento.objects.filter(
        id_centro=request.user.rut.id_centro.id_centro).order_by('codigo')
    caducados = Caducado.objects.filter(
        id_centro=request.user.rut.id_centro.id_centro).order_by('codigo')
    for i in stock:
        print(type(i.codigo.cad_codigo.cantidad))

    if request.method == 'GET':
        criterio_busqueda = request.GET.get('q')
        submitBtn = request.GET.get('submit')
        if criterio_busqueda is not None:
            medicamentos = Medicamento.objects.filter(
                nombre_medicamento__icontains=criterio_busqueda)
            stock = StockMedicamento.objects.filter(codigo__nombre_medicamento__icontains=criterio_busqueda).filter(
                id_centro=request.user.rut.id_centro.id_centro).order_by('codigo')
            paginador = Paginator(stock, 10)
            pagina = request.GET.get('page')
            stock = paginador.get_page(pagina)
            datos = {
                'stock': stock,
                'caducados': caducados,
            }
            parametros = request.GET.copy()

            if 'page' in parametros:
                del parametros['page']

            datos['parametros'] = parametros
            return render(request, 'autofarmapage/listar-medicamento.html', datos)

    if request.method == 'POST':
        caducarBtn = request.POST.get('caducar_btn')
        # print(caducarBtn)
        if caducarBtn is not None:
            cod_medi = request.POST['codigo_med']
            print(cod_medi)
            stock_cadu = request.POST['stock_caducar']
            cod_centro = int(request.user.rut.id_centro.id_centro)
            rut_usuario = int(request.user.rut.rut)
            bd = ConexionBD()
            con = bd.conectar()
            cursor = con.cursor()

            resultado = cursor.var(int)

            cursor.callproc('pkg_administrar_medicamento.sp_caducar_medi', [
                            stock_cadu, cod_centro, cod_medi, resultado])
            print(resultado.getvalue())
            if resultado == 2:
                messages.error(
                    request, 'El Stock total es menor a la cantidad a Caducar.')
            elif resultado == 0:
                messages.error(
                    request, 'Se ha producido un error, por favor intentalo nuevamente.')
        else:
            cod_medicamento = request.POST['codigo_medicamento']
            # print(cod_medicamento)
            stock_add = request.POST['stock_aumentar']
            cod_centro = int(request.user.rut.id_centro.id_centro)
            rut_usuario = int(request.user.rut.rut)

            bd = ConexionBD()
            con = bd.conectar()
            cursor = con.cursor()

            realizado = cursor.var(int)

            cursor.callproc('pkg_administrar_medicamento.sp_aumento_stock', [
                            cod_centro, cod_medicamento, stock_add, realizado])

            # print(realizado.getvalue())
            #medicamentos = Medicamento.objects.all()
        stock = StockMedicamento.objects.filter(
            id_centro=request.user.rut.id_centro.id_centro).order_by('codigo')
        paginador = Paginator(stock, 10)
        pagina = request.GET.get('page')
        stock = paginador.get_page(pagina)
        datos = {
            'stock': stock,
            'caducados': caducados,
        }
        return render(request, 'autofarmapage/listar-medicamento.html', datos)

    paginador = Paginator(stock, 10)
    pagina = request.GET.get('page')
    stock = paginador.get_page(pagina)

    datos = {
        'medicamentos': medicamentos,
        'stock': stock,
    }
    parametros = request.GET.copy()

    if 'page' in parametros:
        del parametros['page']
        datos['parametros'] = parametros

    return render(request, 'autofarmapage/listar-medicamento.html', datos)


# VISTAS MEDICO
def home_medico(request):
    return render(request, 'autofarmapage/home_medico.html', {})


def agregarpaciente(request):
    # Querys para poblar los select del formulario de creacion de persona
    regiones = Region.objects.all()
    ciudades = Comuna.objects.all().order_by('nombre_comuna')
    centro_salud = CentroSalud.objects.all().order_by('id_comuna')

    if request.method == 'POST':
        rut = request.POST['rut']
        rut = rut.replace('.', '')
        rut = rut.replace('-', '')
        rut = rut[0 : len(rut) - 1]
        #dv = request.POST['dv']
        #validador = Validador()
        #if validador.validarRut(rut, dv) == False:
            #messages.error(request, "El rut " + rut +
                           #"- " + dv + " no es válido")
        #else:
        rut = request.POST['rut']
        nombres = request.POST['nombres']
        app_paterno = request.POST['apellido_paterno']
        app_materno = request.POST['apellido_materno']
        telefono = int(request.POST['telefono'])
        email = request.POST['correo_electronico']
        direccion = request.POST['direccion']
        comuna = int(request.POST['id_comuna'])
        centro_s = int(request.POST['id_centro'])
        rut_tutor = None

        # conexión a la bd
        bd = ConexionBD()
        conn = bd.conectar()
        cursor = conn.cursor()
        realizado = cursor.var(int)

        # Llamado al procedimiento almacenado para crear persona (no crea usuario)
        cursor.callproc('pkg_crear_usuario.sp_crear_persona', [
                        rut, nombres, app_paterno, app_materno, telefono, email, direccion, comuna, centro_s, rut_tutor, realizado])
        print(realizado.getvalue())

        if int(realizado.getvalue()) == 1:
            # mensaje exito
            messages.success(request, 'Datos agregados al Sistema.')
            # ----------------ACÁ SERIA CREAR PERSONA
            usuario = Usuario.objects.create_user(rut)
            mensaje_email = 'Tu usuario es ' + \
                rut + ' .Tu contraseña es ' + rut[0:4]

            # envío de mail con el usuario y la contraseña
            send_mail(
                'Bienvenido a Autofarma.',
                mensaje_email,
                'torpedo.page@gmail.com',
                [email],
                fail_silently=False
            )

        elif int(realizado.getvalue()) == 0:
            # mesaje error
            messages.error(
                request, 'Se ha producido un problema y los datos no han sido almacenados. Por Favor intente nuevamente.')
    return render(request, 'autofarmapage/agregar-paciente.html', {'regiones': regiones, 'ciudades': ciudades, 'centro_salud': centro_salud, })


def crearreceta(request):
    persona = Persona.objects.all().filter(id_centro=request.user.rut.id_centro)
    rutpat = None
    nombrePaciente = None
    if request.method == 'GET':
        campo_busqueda = request.GET.get("rutpaciente")
        if campo_busqueda is not None:
            rut = request.GET['rutpaciente']
            for i in persona:
                if i.rut == rut:
                    nombrePaciente = i.nombres + " " + i.apellido_paterno
                    rutpat = i.rut
                    messages.success(request, 'Paciente encontrado')
    elif request.method == 'POST':
        rut_medico = request.POST['rutmedico']
        rutpatiente = request.POST['pacienterut']
        fecha = datetime.now()
        #rut paciente#
        # conexión a la bd
        bd = ConexionBD()
        con = bd.conectar()
        cursor = con.cursor()
        realizado = cursor.var(int)
        retorno = cursor.var(int)
        cursor.callproc('pkg_administrar_receta.sp_nueva_receta', [
                        rut_medico, fecha, rutpatiente, realizado, retorno])
        id_receta = retorno.getvalue()
        if int(realizado.getvalue()) == 1:
            return redirect('crear-receta2', id_receta)
        elif int(realizado.getvalue()) == 0:
            messages.error(request, 'HA OCURRIDO UN ERROR :(')
    return render(request, 'autofarmapage/crear-receta.html', {'nombrePaciente': nombrePaciente, 'rutpat': rutpat})


def crearreceta2(request, id_receta):
    recetapk = Receta.objects.get(id_receta=id_receta)
    tratamiento = TipoTratamiento.objects.all()
    remedios = None
    data5 = {
        'recetapk': recetapk,
        'tratamiento': tratamiento,
        'remedios': remedios
    }
    if request.method == 'GET':
        campo = request.GET.get('q')
        submitBtn = request.GET.get('submit')
        if campo is not None:
            remedios = Medicamento.objects.filter(
                nombre_medicamento__icontains=campo)
            data5 = {
                'recetapk': recetapk,
                'tratamiento': tratamiento,
                'remedios': remedios
            }
            return render(request, 'autofarmapage/crear-receta2.html', data5)
    elif request.method == 'POST':
        posologia = request.POST['posologia']
        duracion = request.POST['duracion']
        dosis = request.POST['dosis']
        tipotratamiento = request.POST['tipo_tratamiento']
        #idreceta = request.POST['idreceta']
        codigo = request.POST['medicamentoadd']
        bd = ConexionBD()
        con = bd.conectar()
        cursor = con.cursor()
        realizado = cursor.var(int)
        cursor.callproc('pkg_administrar_receta.sp_ingresar_detalle_receta', [
                        posologia, duracion, dosis, tipotratamiento, id_receta, codigo, realizado])
        if realizado.getvalue() == 1:
            messages.success(request, "medicamento agregado")
        elif realizado.getvalue() == 0:
            messages.success(request, "hubo un error :(")

    return render(request, 'autofarmapage/crear-receta2.html', data5)


def registrartutor(request):
    # Querys para poblar los select del formulario de creacion de persona
    regiones = Region.objects.all()
    ciudades = Comuna.objects.all().order_by('nombre_comuna')
    centro_salud = CentroSalud.objects.all().order_by('id_comuna')

    if request.method == 'POST':
        rut = request.POST['rut']
        #Quita los puntos, guión y el digito verificador
        rut = rut.replace('.', '')
        rut = rut.replace('-', '')
        rut = rut[0 : len(rut) - 1]
        nombres = request.POST['nombres']
        app_paterno = request.POST['apellido_paterno']
        app_materno = request.POST['apellido_materno']
        telefono = int(request.POST['telefono'])
        email = request.POST['correo_electronico']
        direccion = request.POST['direccion']
        comuna = int(request.POST['id_comuna'])
        centro_s = int(request.POST['id_centro'])
        rut_tutor = None

        # conexión a la bd
        bd = ConexionBD()
        conn = bd.conectar()
        cursor = conn.cursor()
        realizado = cursor.var(int)

        # Llamado al procedimiento almacenado para crear persona (no crea usuario)
        cursor.callproc('pkg_crear_usuario.sp_crear_persona', [
                        rut, nombres, app_paterno, app_materno, telefono, email, direccion, comuna, centro_s, rut_tutor, realizado])
        print(realizado.getvalue())

        if int(realizado.getvalue()) == 1:
            # mensaje exito
            messages.success(request, 'Datos agregados al Sistema.')
            # ----------------ACÁ SERIA CREAR PERSONA
            usuario = Usuario.objects.create_user(rut)
            mensaje_email = 'Tu usuario es ' + \
                rut + ' .Tu contraseña es ' + rut[0:4]

            # envío de mail con el usuario y la contraseña
            send_mail(
                'Bienvenido a Autofarma.',
                mensaje_email,
                'torpedo.page@gmail.com',
                [email],
                fail_silently=False
            )

        elif int(realizado.getvalue()) == 0:
            # mesaje error
            messages.error(
                request, 'Se ha producido un problema y los datos no han sido almacenados. Por Favor intente nuevamente.')
    return render(request, 'autofarmapage/registrar-tutor.html', {'regiones': regiones, 'ciudades': ciudades, 'centro_salud': centro_salud, })


def agregarTutor(request, rut):
    paciente = Persona.objects.get(rut=rut)
    ruttutor = None
    if request.method == 'GET':
        campoBuscar = request.GET.get("busqueda")
        if campoBuscar is not None:
            persona = Persona.objects.all()
            for i in persona:
                if i.rut == campoBuscar:
                    ruttutor = i.rut
                    messages.success(request, 'tutor encontrado')
    elif request.method == 'POST':
        rutdeltutor = request.POST['rutu']
        # conexión a la bd
        bd = ConexionBD()
        con = bd.conectar()
        cursor = con.cursor()
        realizado = cursor.var(int)
        cursor.callproc('pkg_crear_usuario.sp_crear_tutor', [
                        rutdeltutor, paciente.rut, realizado])
        print(realizado.getvalue())
        if realizado.getvalue() == 1:
            return redirect('crear-receta')
        elif realizado.getvalue() == 0:
            messages.error(
                request, 'Ocurrió un error :( - Intente ingresando un rut en el buscador')
    return render(request, 'autofarmapage/agregar-tutor.html', {'paciente': paciente, 'ruttutor': ruttutor})


def verRecetas(request):
    return render(request, 'autofarmapage/ver-recetas.html', {})

# este es la forma con el form de django en el html la vista
# de html que deben usar es la llamada editarpage
    #persona = get_object_or_404(Persona, rut=rut)
    #persona = Persona.objects.get(rut=rut)
    # if request.method == 'GET':
    #    form = RegistrarForm(instance=persona)
    # else:
    #    form = RegistrarForm(request.POST, instance= persona)
    #    if form.is_valid():
    #        form.save()
    #    return redirect('homeadmi')
    # return render(request, 'autofarmapage/editarpage.html', {'form':form})

# no tomar atención a estas lineas
    """bd = ConexionBD()
    conn = bd.conectar()
    cursor = conn.cursor()
   # cursor.execute("select * from persona where rut = 17808528")
    #res = cursor.fetchall()
    #for row in res:
     #   print(row)"""
    """cursor.prepare("select * from persona where rut = :id") 
    cursor.execute(None, id = 15075070)
    res = cursor.
    print(res)"""
    """cursor.prepare("select * from persona where rut = :id")
    cursor.execute(None, id = 15075070)
    ver = cursor.split(".")
    print(ver.index("1"))
    
    data = {
        'res':res
    }"""
