
import pandas as pd
import numpy as np
import random
import os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# Carpetas de trabajo
RUTA_DATA   = 'data'
RUTA_GRAFICOS = 'visualizations'
os.makedirs(RUTA_DATA, exist_ok=True)
os.makedirs(RUTA_GRAFICOS, exist_ok=True)



# CARGAR  DATOS DEL ROL 1

def cargar_datos():
    """
    Lee los tres CSV que generó el Rol 1.
    Si un archivo no existe, el script avisa y detiene la ejecución.
    """
    rutas = {
        'clientes':      os.path.join(RUTA_DATA, 'clientes.csv'),
        'versiones':     os.path.join(RUTA_DATA, 'versiones_software.csv'),
        'instalaciones': os.path.join(RUTA_DATA, 'instalaciones.csv'),
    }

    for nombre, ruta in rutas.items():
        if not os.path.exists(ruta):
            raise FileNotFoundError(
                f"No se encontró '{ruta}'. "
                "Asegúrate de ejecutar primero rol1_generacion_datos.py"
            )

    clientes_df      = pd.read_csv(rutas['clientes'])
    versiones_df     = pd.read_csv(rutas['versiones'])
    instalaciones_df = pd.read_csv(rutas['instalaciones'])

    # para que las columnas de fecha cambien a tipo datetime para poder compararlas
    versiones_df['fecha_release']      = pd.to_datetime(versiones_df['fecha_release'])
    versiones_df['fecha_compilacion']  = pd.to_datetime(versiones_df['fecha_compilacion'])
    instalaciones_df['fecha_instalacion'] = pd.to_datetime(instalaciones_df['fecha_instalacion'])

    print("✔ Datos cargados correctamente")
    print(f"  clientes:      {len(clientes_df)} registros")
    print(f"  versiones:     {len(versiones_df)} registros")
    print(f"  instalaciones: {len(instalaciones_df)} registros")

    return clientes_df, versiones_df, instalaciones_df



# MÉTRICAS DE CALIDAD (DAMA DMBOK)


def medir_completitud(df, nombre_tabla):
    """
    Calcula el porcentaje de celdas que NO son nulas en cada columna.
    Un 100% significa que no falta ningún dato.

    Args:
        df           – DataFrame a analizar
        nombre_tabla – nombre que aparecerá en el reporte

    Returns:
        Lista de diccionarios con los resultados por columna
    """
    resultados = []
    total_filas = len(df)

    for columna in df.columns:
        # count() cuenta solo los valores no nulos
        no_nulos = df[columna].count()
        completitud = (no_nulos / total_filas) * 100

        resultados.append({
            'tabla':        nombre_tabla,
            'columna':      columna,
            'metrica':      'Completitud',
            'valor_actual': round(completitud, 2),
            'umbral':       95.0,   # que lo minimo sea 95%
            'estado':       'OK' if completitud >= 95 else 'ALERTA'
        })

    return resultados


def medir_exactitud_instalaciones(instalaciones_df):
    """
    Verifica que los valores de 'nivel_datos_sensibles' estén entre 1 y 5,
    y que las fechas de instalación estén en el rango del caso (2019–2022).

    Returns:
        Lista de diccionarios con los resultados
    """
    resultados = []

    # Nivel de datos sensibles debe ser 1 a 5
    validos_nivel = instalaciones_df['nivel_datos_sensibles'].between(1, 5).sum()
    pct_validos   = (validos_nivel / len(instalaciones_df)) * 100

    resultados.append({
        'tabla':        'instalaciones',
        'columna':      'nivel_datos_sensibles',
        'metrica':      'Exactitud (rango 1-5)',
        'valor_actual': round(pct_validos, 2),
        'umbral':       100.0,
        'estado':       'OK' if pct_validos == 100 else 'ALERTA'
    })

    #  Fechas entre 2019 y 2022 
    fecha_min = pd.Timestamp('2019-01-01')
    fecha_max = pd.Timestamp('2022-12-31')

    fechas_ok  = instalaciones_df['fecha_instalacion'].between(fecha_min, fecha_max).sum()
    pct_fechas = (fechas_ok / len(instalaciones_df)) * 100

    resultados.append({
        'tabla':        'instalaciones',
        'columna':      'fecha_instalacion',
        'metrica':      'Exactitud (rango 2019-2022)',
        'valor_actual': round(pct_fechas, 2),
        'umbral':       98.0,
        'estado':       'OK' if pct_fechas >= 98 else 'ALERTA'
    })

    return resultados


def medir_consistencia(instalaciones_df, clientes_df, versiones_df):
    """
    Comprueba la integridad referencial:
    - Cada cliente_id en instalaciones debe existir en clientes
    - Cada version_id en instalaciones debe existir en versiones_software

    Si hay IDs huérfanos (que no tienen padre) eso es una inconsistencia.

    Returns:
        Lista de diccionarios con los resultados
    """
    resultados = []

    # Clientes válidos
    clientes_validos = instalaciones_df['cliente_id'].isin(clientes_df['cliente_id'])
    pct_clientes     = (clientes_validos.sum() / len(instalaciones_df)) * 100

    resultados.append({
        'tabla':        'instalaciones',
        'columna':      'cliente_id',
        'metrica':      'Consistencia (integridad referencial)',
        'valor_actual': round(pct_clientes, 2),
        'umbral':       100.0,
        'estado':       'OK' if pct_clientes == 100 else 'ALERTA'
    })

    # Versiones válidas
    versiones_validas = instalaciones_df['version_id'].isin(versiones_df['version_id'])
    pct_versiones     = (versiones_validas.sum() / len(instalaciones_df)) * 100

    resultados.append({
        'tabla':        'instalaciones',
        'columna':      'version_id',
        'metrica':      'Consistencia (integridad referencial)',
        'valor_actual': round(pct_versiones, 2),
        'umbral':       100.0,
        'estado':       'OK' if pct_versiones == 100 else 'ALERTA'
    })

    return resultados


# GENERAR EVENTOS DE SEGURIDAD DataFrame 4

def generar_eventos_seguridad(instalaciones_df, versiones_df, n=200):
    """
    Crea un registro de 200 eventos de seguridad simulados.
    Algunos son normales (accesos, actualizaciones) y otros son anómalos
    (comunicaciones C2, exfiltraciones), que representan el ataque SUNBURST.

    La lógica del caso:
    - Solo las instalaciones con versiones que contienen SUNBURST
      pueden tener eventos de tipo 'Compromiso real'.
    - El resto puede tener eventos sospechosos pero no comprometidos.
    """

    # Unir instalaciones con versiones para saber cuáles tienen SUNBURST
    instalaciones_con_version = instalaciones_df.merge(
        versiones_df[['version_id', 'contiene_sunburst']],
        on='version_id',
        how='left'
    )

    # Separar instalaciones con versión infectada y las  sanas
    infectadas = instalaciones_con_version[
        instalaciones_con_version['contiene_sunburst'] == True
    ]['instalacion_id'].tolist()

    sanas = instalaciones_con_version[
        instalaciones_con_version['contiene_sunburst'] == False
    ]['instalacion_id'].tolist()

    # Tipos de eventos posibles
    tipos_normales   = ['Acceso normal', 'Actualización de software', 'Backup completado', 'Scan de red']
    tipos_sospechosos= ['Login inusual', 'Tráfico inusual', 'Acceso fuera de horario']
    tipos_anomalos   = ['Comunicación C2', 'Exfiltración de datos', 'Backdoor detectado']

    eventos = []
    fecha_base = datetime(2020, 2, 20)  # Fecha en que se compiló SUNBURST

    for i in range(1, n + 1):
        # Elegir si este evento viene de una instalación infectada o sana
        if random.random() < 0.65 and len(infectadas) > 0:
            instalacion_id = random.choice(infectadas)
            es_de_version_infectada = True
        else:
            instalacion_id = random.choice(sanas + infectadas)
            es_de_version_infectada = False

        # Generar timestamp aleatorio entre feb 2020 y dic 2021
        dias_desde_inicio = random.randint(0, 680)
        timestamp = fecha_base + timedelta(days=dias_desde_inicio,
                                           hours=random.randint(0, 23),
                                           minutes=random.randint(0, 59))

        # Decidir tipo de evento y si no es normal
        # Solo las instalaciones con versión infectada pueden tener eventos de Compromiso real
        prob_anomalo = random.random()

        if es_de_version_infectada and prob_anomalo < 0.15:
            # 15% de que el de evento verdaderamente anormal en versión infectada
            tipo_evento = random.choice(tipos_anomalos)
            es_anomalo  = True
            severidad   = random.choice(['Alta', 'Crítica'])
        elif prob_anomalo < 0.10:
            # 10% de que el de evento sospechoso en cualquier instalación
            tipo_evento = random.choice(tipos_sospechosos)
            es_anomalo  = True
            severidad   = 'Media'
        else:
            tipo_evento = random.choice(tipos_normales)
            es_anomalo  = False
            severidad   = random.choice(['Baja', 'Informativa'])

        eventos.append({
            'evento_id':      i,
            'instalacion_id': instalacion_id,
            'timestamp':      timestamp,
            'tipo_evento':    tipo_evento,
            'severidad':      severidad,
            'es_anomalo':     es_anomalo
        })

    eventos_df = pd.DataFrame(eventos)
    eventos_df['timestamp'] = pd.to_datetime(eventos_df['timestamp'])

    # Guardar CSV
    eventos_df.to_csv(os.path.join(RUTA_DATA, 'eventos_seguridad.csv'), index=False)
    print(f"✔ eventos_seguridad.csv generado ({len(eventos_df)} registros)")
    print(f"  Eventos anómalos: {eventos_df['es_anomalo'].sum()}")
    print(f"  Eventos normales: {(~eventos_df['es_anomalo']).sum()}")

    return eventos_df


# REPORTE DE CALIDAD 

def generar_reporte_calidad(clientes_df, versiones_df, instalaciones_df, eventos_df):
    """
    Afirma todos los resultados de las métricas en un solo DataFrame
    y lo guarda como CSV.

    Returns:
        DataFrame con el reporte completo
    """
    todos_resultados = []

    # completar cada tabla
    todos_resultados += medir_completitud(clientes_df,      'clientes')
    todos_resultados += medir_completitud(versiones_df,     'versiones_software')
    todos_resultados += medir_completitud(instalaciones_df, 'instalaciones')
    todos_resultados += medir_completitud(eventos_df,       'eventos_seguridad')

    # que sea exacto
    todos_resultados += medir_exactitud_instalaciones(instalaciones_df)

    # la consistencia
    todos_resultados += medir_consistencia(instalaciones_df, clientes_df, versiones_df)

    reporte_df = pd.DataFrame(todos_resultados)

    # Guardar CSV
    reporte_df.to_csv(os.path.join(RUTA_DATA, 'reporte_calidad.csv'), index=False)
    print(f"\n✔ reporte_calidad.csv generado ({len(reporte_df)} métricas)")

    # Resumen
    alertas = reporte_df[reporte_df['estado'] == 'ALERTA']
    print(f"  Métricas OK:    {len(reporte_df) - len(alertas)}")
    print(f"  Métricas ALERTA: {len(alertas)}")

    return reporte_df



#DETECCIÓN DE ANOMALÍAS

def detectar_anomalias(instalaciones_df, versiones_df, eventos_df):
    """
    Detecta tres tipos de anomalías:
    1. Fechas de instalación anteriores al release de la versión (imposible)
    2. Nivel de datos sensibles fuera del rango 1-5
    3. Eventos con severidad Crítica (los más peligrosos)

    Imprime un resumen en pantalla.
    """
    print("\n" + "="*50)
    print("DETECCIÓN DE ANOMALÍAS")
    print("="*50)

    # Anomalia 1: fecha instalacion < fecha release 
    merged = instalaciones_df.merge(
        versiones_df[['version_id', 'fecha_release']],
        on='version_id',
        how='left'
    )
    anomalias_fechas = merged[merged['fecha_instalacion'] < merged['fecha_release']]
    print(f"\n1. Instalaciones antes del release de la versión: {len(anomalias_fechas)}")
    if len(anomalias_fechas) > 0:
        print("   ⚠ Fechas incoherentes detectadas:")
        print(anomalias_fechas[['instalacion_id', 'fecha_instalacion', 'fecha_release']].to_string(index=False))

    # Anomalia 2: nivel_datos_sensibles fuera de rango
    anomalias_nivel = instalaciones_df[
        ~instalaciones_df['nivel_datos_sensibles'].between(1, 5)
    ]
    print(f"\n2. Niveles de datos sensibles fuera de rango (1-5): {len(anomalias_nivel)}")

    # Anomalia 3: Eventos criticos
    eventos_criticos = eventos_df[eventos_df['severidad'] == 'Crítica']
    print(f"\n3. Eventos con severidad Crítica: {len(eventos_criticos)}")
    print(f"   Tipos: {eventos_criticos['tipo_evento'].value_counts().to_dict()}")

    return anomalias_fechas, anomalias_nivel, eventos_criticos


# PROBLEMA 18,000  <100

def analizar_problema_18000(instalaciones_df, versiones_df):
    """
    Simula y explica la diferencia entre los 18,000 clientes "afectados"
    que anuncio SolarWinds inicialmente y los menos de 100 realmente
    comprometidos.

    Lógica:
    - 18,000 = todos los que descargaron alguna versión (expuestos)
    - ~100    = solo los que tenían versión con SUNBURST (en riesgo)
    - <9      = los que recibieron un ataque de segunda etapa (comprometidos)
    """
    print("\n" + "="*50)
    print("ANÁLISIS: 18,000 vs <100 CLIENTES")
    print("="*50)

    # juntar instalaciones con versiones
    df = instalaciones_df.merge(
        versiones_df[['version_id', 'contiene_sunburst']],
        on='version_id',
        how='left'
    )

    total_instalaciones = len(df)

    expuestos_sunburst = df[df['contiene_sunburst'] == True]
    total_expuestos    = len(expuestos_sunburst)

    # simulamos que solo ~5% de los expuestos fueron
    np.random.seed(SEED)
    n_comprometidos = max(1, int(total_expuestos * 0.05))   # ~5% de expuestos
    comprometidos   = expuestos_sunburst.sample(n=n_comprometidos, random_state=SEED)

    print(f"\n  Total instalaciones (universo inicial): {total_instalaciones}")
    print(f"  Con versión que contiene SUNBURST:      {total_expuestos}")
    print(f"  Realmente comprometidos (2da etapa):    {n_comprometidos}")
    print(f"\n  Reducción: {total_instalaciones} → {total_expuestos} → {n_comprometidos}")
    print("\n  Explicación:")
    print("  SolarWinds reportó inicialmente TODAS las descargas activadas")
    print("  de las versiones afectadas. Pero no todas contenían el malware,")
    print("  y entre las que sí lo tenían, solo un subconjunto fue atacado")
    print("  en la segunda etapa (comunicación con servidores C2 de los atacantes).")

    return total_instalaciones, total_expuestos, n_comprometidos



#VISUALIZACIONES

def crear_visualizaciones(clientes_df, versiones_df, instalaciones_df,
                          eventos_df, reporte_df,
                          total_all, total_expuestos, n_comprometidos):
    """
    Genera 5 gráficos y los guarda como PNG en la carpeta 'visualizations/'.
    """

    # estado de metricas de calidad
    fig, ax = plt.subplots(figsize=(9, 5))
    conteo_estado = reporte_df['estado'].value_counts()
    colores = ['#2ecc71' if s == 'OK' else '#e74c3c' for s in conteo_estado.index]
    ax.bar(conteo_estado.index, conteo_estado.values, color=colores, edgecolor='black')
    ax.set_title('Resultado de Métricas de Calidad (DAMA DMBOK)', fontsize=13, fontweight='bold')
    ax.set_xlabel('Estado')
    ax.set_ylabel('Cantidad de métricas')
    for i, v in enumerate(conteo_estado.values):
        ax.text(i, v + 0.1, str(v), ha='center', fontweight='bold')
    plt.tight_layout()
    ruta = os.path.join(RUTA_GRAFICOS, 'grafico1_metricas_calidad.png')
    plt.savefig(ruta, dpi=150)
    plt.close()
    print(f"✔ Guardado: {ruta}")

    # eventos por severidad 
    fig, ax = plt.subplots(figsize=(8, 5))
    orden_severidad = ['Informativa', 'Baja', 'Media', 'Alta', 'Crítica']
    conteo_sev = eventos_df['severidad'].value_counts().reindex(orden_severidad, fill_value=0)
    colores_sev = ['#3498db', '#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
    ax.bar(conteo_sev.index, conteo_sev.values, color=colores_sev, edgecolor='black')
    ax.set_title('Eventos de Seguridad por Severidad', fontsize=13, fontweight='bold')
    ax.set_xlabel('Severidad')
    ax.set_ylabel('Cantidad de eventos')
    for i, v in enumerate(conteo_sev.values):
        ax.text(i, v + 0.5, str(v), ha='center')
    plt.tight_layout()
    ruta = os.path.join(RUTA_GRAFICOS, 'grafico2_eventos_severidad.png')
    plt.savefig(ruta, dpi=150)
    plt.close()
    print(f"✔ Guardado: {ruta}")

    #   anomalias vs eventos normales 
    fig, ax = plt.subplots(figsize=(6, 6))
    etiquetas = ['Eventos normales', 'Eventos anómalos']
    valores   = [
        (~eventos_df['es_anomalo']).sum(),
        eventos_df['es_anomalo'].sum()
    ]
    colores_pie = ['#2ecc71', '#e74c3c']
    explode     = (0, 0.08)   # resalta la parte anómala
    ax.pie(valores, labels=etiquetas, colors=colores_pie, explode=explode,
           autopct='%1.1f%%', startangle=90)
    ax.set_title('Proporción de Eventos Anómalos vs Normales', fontsize=12, fontweight='bold')
    plt.tight_layout()
    ruta = os.path.join(RUTA_GRAFICOS, 'grafico3_anomalias_pie.png')
    plt.savefig(ruta, dpi=150)
    plt.close()
    print(f"✔ Guardado: {ruta}")

    #Cascada 18,000,expuestos,comprometidos 
    fig, ax = plt.subplots(figsize=(8, 5))
    categorias = [
        'Total\ninstalaciones\n(universo inicial)',
        'Con versión\nSUNBURST\n(en riesgo)',
        'Realmente\ncomprometidos\n(2da etapa)'
    ]
    valores_cascada = [total_all, total_expuestos, n_comprometidos]
    colores_casc    = ['#3498db', '#e67e22', '#e74c3c']
    barras = ax.bar(categorias, valores_cascada, color=colores_casc, edgecolor='black', width=0.5)
    ax.set_title('Reducción de Clientes Afectados\n18,000 → Expuestos → Comprometidos',
                 fontsize=12, fontweight='bold')
    ax.set_ylabel('Cantidad')
    for barra, valor in zip(barras, valores_cascada):
        ax.text(barra.get_x() + barra.get_width() / 2,
                barra.get_height() + 0.3,
                str(valor), ha='center', fontsize=11, fontweight='bold')
    plt.tight_layout()
    ruta = os.path.join(RUTA_GRAFICOS, 'grafico4_cascada_18000.png')
    plt.savefig(ruta, dpi=150)
    plt.close()
    print(f"✔ Guardado: {ruta}")

    # Linea de tiempo de  anormales
    fig, ax = plt.subplots(figsize=(10, 4))
    anomalos = eventos_df[eventos_df['es_anomalo']].copy()
    anomalos['mes'] = anomalos['timestamp'].dt.to_period('M').astype(str)
    conteo_mes = anomalos.groupby('mes').size()
    ax.plot(range(len(conteo_mes)), conteo_mes.values,
            marker='o', color='#e74c3c', linewidth=2)
    ax.set_xticks(range(len(conteo_mes)))
    ax.set_xticklabels(conteo_mes.index, rotation=45, ha='right', fontsize=8)
    ax.set_title('Evolución Mensual de Eventos Anómalos (2020-2021)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mes')
    ax.set_ylabel('Eventos anómalos')
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    ruta = os.path.join(RUTA_GRAFICOS, 'grafico5_timeline_anomalos.png')
    plt.savefig(ruta, dpi=150)
    plt.close()
    print(f"✔ Guardado: {ruta}")


# PROGRAMA PRINCIPAL

if __name__ == "__main__":

    print("=" * 55)
    print("ROL 2 – ANÁLISIS DE CALIDAD DE DATOS | SUNBURST")
    print("=" * 55)

    # Cargar datos del Rol 1
    clientes_df, versiones_df, instalaciones_df = cargar_datos()

    # Generar eventos de seguridad
    print("\n--- Generando eventos de seguridad ---")
    eventos_df = generar_eventos_seguridad(instalaciones_df, versiones_df, n=200)

    # Generar reporte de calidad
    print("\n--- Calculando métricas de calidad ---")
    reporte_df = generar_reporte_calidad(
        clientes_df, versiones_df, instalaciones_df, eventos_df
    )

    # Detectar anormales
    anomalias_fechas, anomalias_nivel, eventos_criticos = detectar_anomalias(
        instalaciones_df, versiones_df, eventos_df
    )

    # Analizar problema 18,000 vs <100
    total_all, total_expuestos, n_comprometidos = analizar_problema_18000(
        instalaciones_df, versiones_df
    )

    # Crear visualizaciones
    print("\n--- Generando gráficos ---")
    crear_visualizaciones(
        clientes_df, versiones_df, instalaciones_df,
        eventos_df, reporte_df,
        total_all, total_expuestos, n_comprometidos
    )

    print("\n" + "=" * 55)
    print("ROL 2 COMPLETADO")
    print("Archivos generados:")
    print("  data/eventos_seguridad.csv")
    print("  data/reporte_calidad.csv")
    print("  visualizations/grafico1_metricas_calidad.png")
    print("  visualizations/grafico2_eventos_severidad.png")
    print("  visualizations/grafico3_anomalias_pie.png")
    print("  visualizations/grafico4_cascada_18000.png")
    print("  visualizations/grafico5_timeline_anomalos.png")
    print("=" * 55)
