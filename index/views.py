from django.shortcuts import render, redirect, get_object_or_404
from .models import Persona, Empresa, Evento
from .forms import CargaIndividualForm, CargaMasivaForm, ActualizarDatos
import pandas as pd
from datetime import datetime
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test

# def is_superuser(user):
#     return user.is_superuser

@login_required
def elegirEvento(request):
    user=request.user
    if user.is_superuser:
        eventos = Evento.objects.all()
        fecha_actual = datetime.now()
        return render(request, 'eventos.html', {'eventos': eventos, 'fecha_actual': fecha_actual})
    else:
        return redirect('login')


@login_required
def db_evento(request, evento_id, evento_nombre):
    evento = Evento.objects.get(pk=evento_id)
    personas = Persona.objects.filter(evento=evento)
    fecha_actual = datetime.now()
    if request.method == 'POST':
        for persona in personas:
            asistencia_key = f'asistencia_{persona.id}'
            asistencia_value = request.POST.get(asistencia_key, 'off') 
            persona.asistencia = asistencia_value == 'on'
            persona.save()
        return HttpResponseRedirect(request.path_info)
    return render(request, 'index.html', {'personas': personas, 'fecha_actual': fecha_actual, 'nombre_evento':evento_nombre})

@login_required
def carga_individual(request, evento_id, evento_nombre):
    evento = Evento.objects.get(pk=evento_id)
    if request.method == 'POST':
        form = CargaIndividualForm(request.POST)
        if form.is_valid():
            dni = form.cleaned_data['dni']        
        if Persona.objects.filter(dni=dni, evento=evento).exists():
            messages.error(request, f'El DNI {dni} ya existe en la base de datos.')
        else:
            nombre_empresa = form.cleaned_data['empresa']
            empresa, _ = Empresa.objects.get_or_create(nombre=nombre_empresa)
            evento_nombre = evento.nombre
            Persona.objects.create(
                nombreyapellido=form.cleaned_data['nombreyapellido'],
                dni=form.cleaned_data['dni'],
                empresa=empresa,
                acceso=form.cleaned_data['acceso'],
                asistencia=form.cleaned_data['asistencia'],
                observaciones=form.cleaned_data.get('observaciones', ''),
                fechaHastaSeguro=form.cleaned_data.get('fechaHastaSeguro', None),
                evento=evento
            )
            url = reverse('db_evento', args=[evento_id, evento_nombre])
            return redirect(url)
    else:
        form = CargaIndividualForm()
    return render(request, 'cargaIndividual.html', {'form': form, 'evento': evento})

@login_required    
def carga_masiva(request, evento_id, evento_nombre):
    evento = Evento.objects.get(pk=evento_id)
    if request.method == 'GET':
        return render(request, 'cargaMasiva.html', {'form': CargaMasivaForm()})
    else:
        archivo = request.FILES['archivo_excel']
        if archivo.name.endswith('.xls') or archivo.name.endswith('.xlsx'):
            df = pd.read_excel(archivo) # Lee el archivo Excel usando pandas
            dni_existentes = list(Persona.objects.values_list('dni', flat=True))
            for _, row in df.iterrows():
                dni = row['DNI']
                if dni in dni_existentes:
                    previous_url = request.META.get('HTTP_REFERER') 
                    messages.error(request, f'El DNI {dni} ya existe en la base de datos.')
                    return render(request,'error.html',{'previous_url': previous_url})  # Redirige a una vista de error
                else:
                    empresa_nombre = row['EMPRESA']
                    empresa, _ = Empresa.objects.get_or_create(nombre=empresa_nombre)
                    nombreyapellido=row['NOMBRE Y APELLIDO']
                    acceso=row['ACCESO']
                    observaciones=row.get('OBSERVACIONES', '')
                    fechaHastaSeguro=row.get('FECHA HASTA', None)
                    try:
                        fechaHastaSeguro = datetime.fromisoformat(fechaHastaSeguro)
                    except (ValueError, TypeError):
                        fechaHastaSeguro = None 

                    observaciones = observaciones if observaciones else None
                    fechaHastaSeguro = fechaHastaSeguro if fechaHastaSeguro  else None

                    Persona.objects.create(
                    dni=dni,
                    nombreyapellido=nombreyapellido,
                    empresa=empresa,
                    acceso=acceso,
                    asistencia=False,
                    observaciones=observaciones,
                    fechaHastaSeguro=fechaHastaSeguro,
                    evento=evento,
                    )
            evento_nombre = evento.nombre
            url = reverse('db_evento', args=[evento_id, evento_nombre])
            return redirect(url)
        else:
            return render(request, 'error.html', {'mensaje': 'El archivo no es un archivo Excel válido.'})

def error_view(request):
    return render(request, 'error.html')

# para editar datos de persona - falta agregar el forms a boton editar de Front.
@login_required
def actualizar_datos(request):
    if request.method == 'POST':
        form = ActualizarDatos(request.POST)
        if form.is_valid():
            form.save()
            return redirect (db_evento)
        else:
            form = ActualizarDatos()
        return render (request, 'index.html', {'form':form})