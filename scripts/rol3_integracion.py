
import pandas as pd
import numpy as np
import random
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


SEED = 42
np.random.seed(SEED)
random.seed(SEED)

RUTA_DATA      = 'data'
RUTA_GRAFICOS  = 'visualizations'
os.makedirs(RUTA_DATA, exist_ok=True)
os.makedirs(RUTA_GRAFICOS, exist_ok=True)



def cargar_todos_los_datos():
    """
    Carga los 5 archivos CSV generados por los Roles 1 y 2.
    Verifica que existan antes de intentar leerlos.

    Returns:
        Tupla con los 5 DataFrames
    """
    archivos = {
        'clientes':          'clientes.csv',
        'versiones':         'versiones_software.csv',
        'instalaciones':     'instalaciones.csv',
        'eventos':           'eventos_seguridad.csv',
        'reporte_calidad':   'reporte_calidad.csv',
    }

    dataframes = {}
    for clave, archivo in archivos.items():
        ruta = os.path.join(RUTA_DATA, archivo)
        if not os.path.exists(ruta):
            raise FileNotFoundError(
                f"No se encontró '{ruta}'.\n"
                "Asegúrate de ejecutar primero:\n"
                "  1) rol1_generacion_datos.py\n"
                "  2) rol2_calidad_datos.py"
            )
        dataframes[clave] = pd.read_csv(ruta)
        print(f"✔ Cargado: {archivo} ({len(dataframes[clave])} registros)")

    # Convertir las fechas a datetime donde aplique
    dataframes['versiones']['fecha_release']         = pd.to_datetime(dataframes['versiones']['fecha_release'])
    dataframes['versiones']['fecha_compilacion']     = pd.to_datetime(dataframes['versiones']['fecha_compilacion'])
    dataframes['instalaciones']['fecha_instalacion'] = pd.to_datetime(dataframes['instalaciones']['fecha_instalacion'])
    dataframes['eventos']['timestamp']               = pd.to_datetime(dataframes['eventos']['timestamp'])

    return (
        dataframes['clientes'],
        dataframes['versiones'],
        dataframes['instalaciones'],
        dataframes['eventos'],
        dataframes['reporte_calidad']
    )



#CREAR DATAFRAME CONSOLIDADO

def crear_dataframe_consolidado(clientes_df, versiones_df,
                                 instalaciones_df, eventos_df):
    """
    Une todos los DataFrames en uno solo usando pandas merge().

    El proceso es:
    eventos → merge con instalaciones (por instalacion_id)
            → merge con clientes      (por cliente_id)
            → merge con versiones     (por version_id)

    Esto nos da un DataFrame plano con toda la información junta,
    útil para análisis integrado.

    Returns:
        DataFrame consolidado
    """
    print("\n--- Paso 1: unir eventos con instalaciones ---")
    # Left join: conservamos todos los eventos, aunque no tengan instalación
    paso1 = eventos_df.merge(
        instalaciones_df,
        on='instalacion_id',
        how='left',
        suffixes=('_evento', '_instalacion')   # evita conflicto de nombres
    )
    print(f"  Registros después del primer merge: {len(paso1)}")

    print("--- Paso 2: unir con clientes ---")
    paso2 = paso1.merge(
        clientes_df,
        on='cliente_id',
        how='left'
    )
    print(f"  Registros después del segundo merge: {len(paso2)}")

    print("--- Paso 3: unir con versiones de software ---")
    consolidado_df = paso2.merge(
        versiones_df[['version_id', 'nombre_version', 'contiene_sunburst',
                      'fecha_release', 'fecha_compilacion']],
        on='version_id',
        how='left'
    )
    print(f"  Registros finales en el DataFrame consolidado: {len(consolidado_df)}")

    # Guardar el consolidado
    consolidado_df.to_csv(
        os.path.join(RUTA_DATA, 'consolidado.csv'), index=False
    )
    print("✔ consolidado.csv guardado")

    return consolidado_df


#MAPEO AL CICLO DE VIDA DE DATOS 


MAPA_CICLO_VIDA = {
    # eventos donde se generan datos nuevos
    'Acceso normal':               ('Uso',          'Data Operations'),
    'Actualización de software':   ('Mantenimiento', 'Data Architecture'),
    'Backup completado':           ('Archivo',       'Data Storage & Operations'),
    'Scan de red':                 ('Uso',           'Data Security'),
    'Login inusual':               ('Uso',           'Data Security'),
    'Tráfico inusual':             ('Uso',           'Data Security'),
    'Acceso fuera de horario':     ('Uso',           'Data Security'),
    #cuando el atacante crea y extrae datos
    'Comunicación C2':             ('Creación',      'Data Security'),
    'Exfiltración de datos':       ('Eliminación',   'Data Security'),
    'Backdoor detectado':          ('Mantenimiento', 'Data Security'),
}

def mapear_ciclo_vida(consolidado_df):
    """
    Agrega columnas 'fase_ciclo_vida' y 'area_dama' al DataFrame consolidado,
    basándose en el tipo de evento.

    Returns:
        DataFrame con las fases del ciclo de vida asignadas
    """
    # Extraer la fase del ciclo de vida a partir del tipo de evento
    consolidado_df['fase_ciclo_vida'] = consolidado_df['tipo_evento'].map(
        lambda tipo: MAPA_CICLO_VIDA.get(tipo, ('Uso', 'Data Operations'))[0]
    )

    # Extraer el area del DAMA correspondiente
    consolidado_df['area_dama'] = consolidado_df['tipo_evento'].map(
        lambda tipo: MAPA_CICLO_VIDA.get(tipo, ('Uso', 'Data Operations'))[1]
    )

    print("\n✔ Fases del ciclo de vida asignadas")
    print("\nDistribución por fase:")
    print(consolidado_df['fase_ciclo_vida'].value_counts().to_string())

    return consolidado_df



# GENERAR eventos_ciclo_vida

def generar_eventos_ciclo_vida(consolidado_df):
    """
    Crea el DataFrame 6: eventos_ciclo_vida.
    Es un subconjunto del consolidado con solo las columnas relevantes
    para el análisis del ciclo de vida.

    Returns:
        DataFrame eventos_ciclo_vida
    """
    eventos_cv_df = consolidado_df[[
        'evento_id',
        'fase_ciclo_vida',
        'timestamp',
        'tipo_evento',
        'area_dama'
    ]].copy()

    # cambiar timestamp a  fecha para que de 
    eventos_cv_df = eventos_cv_df.rename(columns={
        'timestamp':   'fecha',
        'tipo_evento': 'descripcion'
    })

    eventos_cv_df.to_csv(
        os.path.join(RUTA_DATA, 'eventos_ciclo_vida.csv'), index=False
    )
    print(f"\n✔ eventos_ciclo_vida.csv generado ({len(eventos_cv_df)} registros)")

    return eventos_cv_df



#Generar resumen_impacto

def generar_resumen_impacto(consolidado_df, versiones_df):
    """
    Crea el DataFrame 7: resumen_impacto.

    Para cada versión calcula:
    - total_instalaciones: cuántas veces se instaló
    - clientes_expuestos:  cuántos clientes únicos la instalaron
    - clientes_comprometidos: cuántos tuvieron al menos un evento crítico
      (solo posible en versiones con SUNBURST)

    Returns:
        DataFrame resumen_impacto
    """
    resumen_filas = []

    for _, version in versiones_df.iterrows():
        vid = version['version_id']

        # Filtrar instalaciones de esta version
        instalaciones_version = consolidado_df[
            consolidado_df['version_id'] == vid
        ]

        total_inst      = len(instalaciones_version)
        clientes_unicos = instalaciones_version['cliente_id'].nunique()

        # Comprometidos = clientes con al menos 1 evento solo tiene sentido si la version tiene SUNBURST
        if version['contiene_sunburst']:
            comprometidos_df = instalaciones_version[
                instalaciones_version['severidad'] == 'Crítica'
            ]
            clientes_comprometidos = comprometidos_df['cliente_id'].nunique()
        else:
            clientes_comprometidos = 0

        resumen_filas.append({
            'version_id':             vid,
            'nombre_version':         version['nombre_version'],
            'contiene_sunburst':      version['contiene_sunburst'],
            'total_instalaciones':    total_inst,
            'clientes_expuestos':     clientes_unicos,
            'clientes_comprometidos': clientes_comprometidos
        })

    resumen_df = pd.DataFrame(resumen_filas)

    resumen_df.to_csv(
        os.path.join(RUTA_DATA, 'resumen_impacto.csv'), index=False
    )
    print(f"✔ resumen_impacto.csv generado ({len(resumen_df)} registros)")
    print("\nResumen de impacto por versión:")
    print(resumen_df[['nombre_version', 'total_instalaciones',
                       'clientes_expuestos', 'clientes_comprometidos']].to_string(index=False))

    return resumen_df



# Visualizaciones

def crear_dashboard(consolidado_df, resumen_df, eventos_cv_df):
    """
    Genera un dashboard con 4 subgráficos en una sola imagen:
      1. Instalaciones por versión (separando versiones con/sin SUNBURST)
      2. Cascada: instalaciones → expuestos → comprometidos
      3. Eventos por fase del ciclo de vida
      4. Línea de tiempo del ataque (eventos anómalos por mes)
    """

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(
        'Dashboard Integrado – Análisis SUNBURST (SolarWinds)\nRol 3: Integración y Ciclo de Vida de Datos',
        fontsize=15, fontweight='bold', y=0.98
    )

    # Crear cuadricula de subgraficos: 2 filas, 2 columnas
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    # Instalaciones por version
    ax1 = fig.add_subplot(gs[0, 0])
    colores_version = [
        '#e74c3c' if s else '#2ecc71'
        for s in resumen_df['contiene_sunburst']
    ]
    barras = ax1.barh(
        resumen_df['nombre_version'],
        resumen_df['total_instalaciones'],
        color=colores_version,
        edgecolor='black'
    )
    ax1.set_title('Instalaciones por Versión\n(rojo = contiene SUNBURST)', fontsize=10)
    ax1.set_xlabel('Total instalaciones')
    for barra in barras:
        ancho = barra.get_width()
        ax1.text(ancho + 0.1, barra.get_y() + barra.get_height() / 2,
                 str(int(ancho)), va='center', fontsize=8)

    # Cascada de impacto 
    ax2 = fig.add_subplot(gs[0, 1])
    total_instalaciones   = resumen_df['total_instalaciones'].sum()
    total_expuestos       = resumen_df.loc[resumen_df['contiene_sunburst'], 'clientes_expuestos'].sum()
    total_comprometidos   = resumen_df['clientes_comprometidos'].sum()

    categorias = ['Total\ninstalaciones', 'Clientes\nexpuestos', 'Comprometidos\n(2da etapa)']
    valores    = [total_instalaciones, total_expuestos, total_comprometidos]
    colores_c  = ['#3498db', '#e67e22', '#e74c3c']
    barras2    = ax2.bar(categorias, valores, color=colores_c, edgecolor='black', width=0.5)
    ax2.set_title('Cascada de Impacto SUNBURST\n(18,000 → expuestos → comprometidos)', fontsize=10)
    ax2.set_ylabel('Cantidad')
    for barra, val in zip(barras2, valores):
        ax2.text(barra.get_x() + barra.get_width() / 2,
                 barra.get_height() + 0.2,
                 str(val), ha='center', fontweight='bold')

    # Eventos por fase del ciclo de vida 
    ax3 = fig.add_subplot(gs[1, 0])
    orden_fases = ['Planificación', 'Creación', 'Mantenimiento', 'Uso', 'Archivo', 'Eliminación']
    conteo_fases = (
        consolidado_df['fase_ciclo_vida']
        .value_counts()
        .reindex(orden_fases, fill_value=0)
    )
    colores_fases = ['#9b59b6', '#e74c3c', '#e67e22', '#3498db', '#1abc9c', '#95a5a6']
    ax3.bar(conteo_fases.index, conteo_fases.values,
            color=colores_fases, edgecolor='black')
    ax3.set_title('Eventos por Fase del Ciclo de Vida\n(DAMA DMBOK)', fontsize=10)
    ax3.set_xlabel('Fase')
    ax3.set_ylabel('Cantidad de eventos')
    ax3.tick_params(axis='x', rotation=25)
    for i, v in enumerate(conteo_fases.values):
        ax3.text(i, v + 0.3, str(v), ha='center', fontsize=9)

    # Timeline de  anomalos 
    ax4 = fig.add_subplot(gs[1, 1])
    anomalos = consolidado_df[consolidado_df['es_anomalo'] == True].copy()
    anomalos['mes'] = anomalos['timestamp'].dt.to_period('M').astype(str)
    conteo_mes = anomalos.groupby('mes').size()

    ax4.fill_between(range(len(conteo_mes)), conteo_mes.values,
                     color='#e74c3c', alpha=0.3)
    ax4.plot(range(len(conteo_mes)), conteo_mes.values,
             marker='o', color='#e74c3c', linewidth=2)
    ax4.set_xticks(range(len(conteo_mes)))
    ax4.set_xticklabels(conteo_mes.index, rotation=45, ha='right', fontsize=7)
    ax4.set_title('Evolución Mensual de Eventos Anómalos\n(Feb 2020 – Dic 2021)', fontsize=10)
    ax4.set_xlabel('Mes')
    ax4.set_ylabel('Eventos anómalos')
    ax4.grid(axis='y', linestyle='--', alpha=0.4)

    # Guardar dashboard
    ruta_dashboard = os.path.join(RUTA_GRAFICOS, 'dashboard_rol3.png')
    plt.savefig(ruta_dashboard, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n✔ Dashboard guardado: {ruta_dashboard}")

    return ruta_dashboard



if __name__ == "__main__":

    print("=" * 55)
    print("ROL 3 – INTEGRACIÓN DE DATOS | SUNBURST")
    print("=" * 55)

    # 1. Cargar todos los datos
    print("\n--- Cargando todos los CSV ---")
    (clientes_df, versiones_df, instalaciones_df,
     eventos_df, reporte_calidad_df) = cargar_todos_los_datos()

    # 2. Crear DataFrame consolidado
    print("\n--- Creando DataFrame consolidado ---")
    consolidado_df = crear_dataframe_consolidado(
        clientes_df, versiones_df, instalaciones_df, eventos_df
    )

    # 3. Mapear al ciclo de vida de datos
    print("\n--- Mapeando al Ciclo de Vida de Datos (DAMA DMBOK) ---")
    consolidado_df = mapear_ciclo_vida(consolidado_df)

    # 4. Generar DataFrame 6: eventos_ciclo_vida
    eventos_cv_df = generar_eventos_ciclo_vida(consolidado_df)

    # 5. Generar DataFrame 7: resumen_impacto
    print("\n--- Generando resumen de impacto por versión ---")
    resumen_df = generar_resumen_impacto(consolidado_df, versiones_df)

    # 6. Identificar clientes comprometidos
    print("\n--- Clientes realmente comprometidos ---")
    comprometidos = consolidado_df[
        (consolidado_df['es_anomalo'] == True) &
        (consolidado_df['severidad']  == 'Crítica') &
        (consolidado_df['contiene_sunburst'] == True)
    ]['nombre_organizacion'].unique()
    print(f"  Organizaciones con eventos críticos en versiones SUNBURST: {len(comprometidos)}")

    # 7. Crear dashboard
    print("\n--- Generando dashboard ---")
    crear_dashboard(consolidado_df, resumen_df, eventos_cv_df)

    print("\n" + "=" * 55)
    print("ROL 3 COMPLETADO")
    print("Archivos generados:")
    print("  data/consolidado.csv")
    print("  data/eventos_ciclo_vida.csv")
    print("  data/resumen_impacto.csv")
    print("  visualizations/dashboard_rol3.png")
    print("=" * 55)
