import pandas as pd
import numpy as np
from faker import Faker
import random
import os
from datetime import timedelta

# Semilla para que los datos salgan iguales cada vez
seed = 42

np.random.seed(seed)
random.seed(seed)
Faker.seed(seed) 

# Faker para generar nombres de organizaciones realistas pero ficticios
fake = Faker()

# Carpeta donde se guardan los csv
RUTA_DATA = 'data'
os.makedirs(RUTA_DATA, exist_ok=True)  # Si la carpeta no existe, la crea


# Generar tabla clientes
def generar_clientes(n=50):

    sectores = [
        'Tecnología',
        'Ciberseguridad',
        'Gobierno',
        'Finanzas',
        'Operaciones de red'
    ]

    paises = [
        'Estados Unidos',
        'México',
        'Costa Rica',
        'Perú',
        'Colombia'
    ]

    clientes = []

    for i in range(1, n + 1):

        clientes.append({
            'cliente_id': i,
            'nombre_organizacion': fake.company(),
            'tipo_org': random.choice([
                'Pública',
                'Privada',
                'Académica'
            ]),

            'pais': random.choice(paises),
            'sector': random.choice(sectores),
            'criticidad': random.choice([
                'Alta',
                'Media',
                'Baja'
            ])
        })

    
    clientes_df = pd.DataFrame(clientes)

    # Exportar a CSV
    clientes_df.to_csv(
        os.path.join(RUTA_DATA, 'clientes.csv'),
        index=False
    )
    print("clientes.csv generado")
    return clientes_df


# Generar tabla versiones
def generar_versiones():

    versiones = [

        {
            'version_id': 101,
            'nombre_version': 'Orion 2019.4',
            'fecha_release': '2019-06-15',
            'contiene_sunburst': True,
            'fecha_compilacion': '2020-02-20'
        },

        {
            'version_id': 102,
            'nombre_version': 'Orion 2019.4 HF1',
            'fecha_release': '2019-09-10',
            'contiene_sunburst': True,
            'fecha_compilacion': '2020-02-20'
        },

        {
            'version_id': 103,
            'nombre_version': 'Orion 2019.4 HF2',
            'fecha_release': '2019-12-01',
            'contiene_sunburst': True,
            'fecha_compilacion': '2020-02-20'
        },

        {
            'version_id': 104,
            'nombre_version': 'Orion 2019.4 HF5',
            'fecha_release': '2020-03-26',
            'contiene_sunburst': False,
            'fecha_compilacion': '2020-03-20'
        },

        {
            'version_id': 105,
            'nombre_version': 'Orion 2020.2',
            'fecha_release': '2020-05-10',
            'contiene_sunburst': True,
            'fecha_compilacion': '2020-02-20'
        },

        {
            'version_id': 106,
            'nombre_version': 'Orion 2020.2 HF1',
            'fecha_release': '2020-08-15',
            'contiene_sunburst': True,
            'fecha_compilacion': '2020-02-20'
        },

        {
            'version_id': 107,
            'nombre_version': 'Orion 2020.2.1',
            'fecha_release': '2020-10-10',
            'contiene_sunburst': False,
            'fecha_compilacion': '2020-10-01'
        },

        {
            'version_id': 108,
            'nombre_version': 'Orion 2021.1',
            'fecha_release': '2021-01-15',
            'contiene_sunburst': False,
            'fecha_compilacion': '2021-01-05'
        }

    ]

    versiones_df = pd.DataFrame(versiones)
    versiones_df['fecha_release'] = pd.to_datetime(
        versiones_df['fecha_release']
    )
    versiones_df['fecha_compilacion'] = pd.to_datetime(
        versiones_df['fecha_compilacion']
    )
    versiones_df.to_csv(
        os.path.join(RUTA_DATA, 'versiones_software.csv'),
        index=False
    )
    print("versiones_software.csv generado")
    return versiones_df


# Generar tabla instalaciones
def generar_instalaciones(clientes_df, versiones_df, n=100):

    instalaciones = []
    for i in range(1, n + 1):
        cliente_id = int(
            np.random.choice(clientes_df['cliente_id'])
        )
        version_id = int(
            np.random.choice(versiones_df['version_id'])
        )

        # Buscar fecha release de la versión
        fecha_release = versiones_df.loc[
            versiones_df['version_id'] == version_id,
            'fecha_release'
        ].values[0]    # Extraer el valor único de la fecha para poder hacer la suma de días

        dias_despues = np.random.randint(15, 300)
        fecha_instalacion = (
            fecha_release + timedelta(days=int(dias_despues)) # Días después de la salida de la versión
        )

        instalaciones.append({

            'instalacion_id': i,
            'cliente_id': cliente_id,
            'version_id': version_id,
            'fecha_instalacion': fecha_instalacion,
           'nivel_datos_sensibles': random.randint(1, 5)
        })


    # Convertir a DataFrame
    instalaciones_df = pd.DataFrame(instalaciones)

    #Cambiar las fechas a formato datetime para poder filtrar, comparar y ordenar 
    instalaciones_df['fecha_instalacion'] = pd.to_datetime( instalaciones_df['fecha_instalacion'])

    # Exportar a CSV
    instalaciones_df.to_csv(
        os.path.join(RUTA_DATA, 'instalaciones.csv'),
        index=False
    )
    print("instalaciones.csv generado")
    return instalaciones_df

def generar_diccionario(clientes_df, versiones_df, instalaciones_df):

    os.makedirs('docs', exist_ok=True)
    
    tablas = [
        ('CLIENTES', clientes_df), 
        ('VERSIONES_SOFTWARE', versiones_df), 
        ('INSTALACIONES', instalaciones_df)
    ]
    
    with open('docs/Diccionario_de_Datos.txt', 'w', encoding='utf-8') as f:
        for nombre, df in tablas:
            print(f"TABLA: {nombre} ({len(df)} registros)", file=f)
            
            for col in df.columns:
                # Extrae directamente el tipo de dato original de Pandas (int64, object, etc.)
                tipo = df[col].dtype
                
                # Lo escribe directamente en el archivo
                print(f"  • {col}: {tipo}", file=f)
                
        
    
# Ejecutar todo
if __name__ == "__main__":

    print("Generando datos")

    clientes_df = generar_clientes(50)
    versiones_df = generar_versiones()
    instalaciones_df = generar_instalaciones(
        clientes_df,
        versiones_df,
        100
    )

#Verificar que los ids existan en las otras tablas

    clientes_validos = instalaciones_df['cliente_id'].isin(  
        clientes_df['cliente_id']
    ).all()  #.all() verifica que todos los valores sean True, si fallan da False


#Comprueba que cada versión instalada realmente exista en la tabla padre.
    versiones_validas = instalaciones_df['version_id'].isin(
        versiones_df['version_id']
    ).all()

    if clientes_validos and versiones_validas:
        print("Integridad correcta")
    else:
        print("Error en relaciones")

    print("\nCLIENTES")
    print(clientes_df.head())

    print("\nVERSIONES")
    print(versiones_df.head())

    print("\nINSTALACIONES")
    print(instalaciones_df.head())

    print("\nDatos generados")

    generar_diccionario(clientes_df, versiones_df, instalaciones_df)
    print("Diccionario generado")