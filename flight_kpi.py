# author Nathalie C <n.crevenat@gmail.com>
# date 13/05/2024

import argparse
import pandas as pd
import xml.etree.ElementTree as ET
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import requests
import ast


def get_elevation_data(lat_lon_pairs, lot):
    base_url = "https://wxs.ign.fr/calcul/alti/rest/elevation.json"
    lat_lon_elev = {}
    for i in range(0, len(lat_lon_pairs), lot):
        batch = lat_lon_pairs[i:i+lot]
        lat_values = "|".join(str(pair[0]) for pair in batch)
        lon_values = "|".join(str(pair[1]) for pair in batch)
        response = requests.get(f"{base_url}?lon={lon_values}&lat={lat_values}&zonly=true")
        if response.status_code == 200:
            elevations = json.loads(response.text)['elevations']
            for j in range(len(batch)):
                lat_lon_elev[(batch[j][0], batch[j][1])] = elevations[j]
        else:
            print(f"Error: {response.status_code}")
    return lat_lon_elev

def parse_gpx_file(gpx_file):
    tree = ET.parse(gpx_file)
    root = tree.getroot()
    ns = {'default': 'http://www.topografix.com/GPX/1/1'}
    lat_lon_pairs = [[float(pt.attrib['lat']), float(pt.attrib['lon'])] for pt in root.findall('.//default:trkpt', ns)]
    return lat_lon_pairs



def process_data(gpx_file,  outputDir, type_analyse, optionsAnalyse, ecartTemps):
    lat_lon_pairs = parse_gpx_file(gpx_file)
    elevation_data = get_elevation_data(lat_lon_pairs, 100)

    # Lire le fichier GPX
    tree = ET.parse(gpx_file)
    root = tree.getroot()

    ns = {'default': 'http://www.topografix.com/GPX/1/1',
          'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}
    
    metadata_time = root.find('default:metadata/default:time', ns)
    time_gps_trace = ''
    if metadata_time is not None:
        dt = datetime.strptime(metadata_time.text, "%Y-%m-%dT%H:%M:%S.%fZ")
        time_gps_trace = dt.strftime("%Y-%m-%d_%H-%M")


    tree = ET.parse(gpx_file)
    root = tree.getroot()

    data = []
    metadata_time = root.find('default:metadata/default:time', ns)
    time_gps_trace = ''
    if metadata_time is not None:
        dt = datetime.strptime(metadata_time.text, "%Y-%m-%dT%H:%M:%S.%fZ")
        time_gps_trace = dt.strftime("%Y-%m-%d_%H-%M")


    for trkpt in root.findall('.//default:trkpt', ns):
        altitude_mer = trkpt.find('default:ele', ns).text
        time = trkpt.find('default:time', ns).text
        extensions = trkpt.find('default:extensions', ns)
        fc = extensions.find('gpxtpx:TrackPointExtension/gpxtpx:hr', ns).text
        lat = float(trkpt.attrib['lat'])
        lon = float(trkpt.attrib['lon'])
        elevation_sol = elevation_data.get((lat, lon))
        data.append([time, altitude_mer, lat, lon, elevation_sol, fc,time])

    df = pd.DataFrame(data, columns=['datetime', 'altitude_mer', 'lat', 'lon', 'elevation_sol', 'fc', 'time_hm'])
    # on garde une seule valeur par seconde
    df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_convert('Europe/Paris').dt.floor('min')
    df = df.drop_duplicates(subset='datetime', keep='first')
    df['datetime'] = df['datetime'].dt.strftime('%d/%m/%Y %H:%M:%S')
    df['time_hm'] = pd.to_datetime(df['time_hm']).dt.tz_convert('Europe/Paris').dt.floor('min')
    df['time_hm'] = df['time_hm'].dt.strftime('%H:%M')
    df['altitude_mer'] = df['altitude_mer'].astype(float).round(1)
    df['elevation_sol'] = df['altitude_mer']  - df['elevation_sol'].astype(float)
    df['elevation_sol'] = df['elevation_sol'].astype(float).round(1)
    df['fc'] = df['fc'].astype(float).round(1)
    df['vario'] = df['altitude_mer'].diff().round(1)    
    df['delta_fc'] = df['fc'].diff().round(1)

    df['Time'] = pd.to_datetime(df['datetime'])
    df.set_index('Time', inplace=True)
    df = df.resample(ecartTemps).first().dropna()

    # export csv
    df.to_csv(outputDir + 'raw_' + time_gps_trace + '.csv', sep=';', index=False)

    # Créer une figure et un axe
    fig, ax1 = plt.subplots(figsize=(15, 5))

    # axe de gauche
    ax1.plot(df['time_hm'], df['delta_fc'], color='green',  label='Delta FC')
    ax1.set_xlabel('Heure (finesse point : ' + str(ecartTemps)  + ')')
    ax1.tick_params(axis='y')

    nb_lignes = df.shape[0]
    ecart_tick = nb_lignes//20
    for i, label in enumerate(ax1.xaxis.get_ticklabels()):
        if i % ecart_tick != 0:  # on rend visible que 1 tick sur n
            label.set_visible(False)

    if type_analyse == "vario":                   
        # Ajouter des lignes verticales rouges quand  fc augmente et vario > 2
        mask_red = (df['delta_fc'] > 0) & (df['vario'] > optionsAnalyse[1])
        index_legend = 0
        for i in df['time_hm'][mask_red]:
            if index_legend == 0:
                ax1.axvline(x=i, color='red', alpha=1, label='Vario > '+ str(optionsAnalyse[1])+' et FC montante')
            else:
                ax1.axvline(x=i, color='red', alpha=1)
            index_legend+=1

    
        # Ajouter des lignes verticales bleues quand fc augmenteet vario < -3
        mask_blue = (df['delta_fc'] >0) & (df['vario'] < optionsAnalyse[0])
        index_legend = 0
        for i in df['time_hm'][mask_blue]:
            if index_legend == 0:
                ax1.axvline(x=i, color='blue', alpha=1, label='Vario < '+ str(optionsAnalyse[0]) +' et FC montante')
            else:
                ax1.axvline(x=i, color='blue', alpha=1)
            index_legend+=1

        # Ajouter des lignes verticales vertes quand fc stable ou descendante et vario < -3
        mask_green = (df['delta_fc'] <=0) & (df['vario'] < optionsAnalyse[0])
        index_legend = 0
        for i in df['time_hm'][mask_green]:
            if index_legend == 0:
                ax1.axvline(x=i, color='green', alpha=0.5, label='Vario < '+ str(optionsAnalyse[0]) +' et FC stable')
            else:
                ax1.axvline(x=i, color='green', alpha=0.5)
            index_legend+=1

        # Ajouter des lignes verticales vertes quand fc stable ou descendante et vario > 2
        mask_yellow = (df['delta_fc'] <=0) & (df['vario'] > optionsAnalyse[1])
        index_legend = 0
        for i in df['time_hm'][mask_yellow]:
            if index_legend == 0:
                ax1.axvline(x=i, color='yellow', alpha=0.5, label='Vario > '+ str(optionsAnalyse[1]) +' et FC stable')
            else:
                ax1.axvline(x=i, color='yellow', alpha=0.5)
            index_legend+=1

        # vario a droite
        ax1.plot(df['time_hm'], df['vario'], color='grey', label='Vario')
        # Créer un deuxième axe des y pour la FC
        ax2 = ax1.twinx()
        ax2.plot(df['time_hm'], df['fc'], color='purple', label='FC')

        # Titre du graphique
        plt.title('Vario et variation FC dans le temps')


    if type_analyse == "altitude":                   
        # Ajouter des lignes verticales rouges quand elevation_sol < 100 et fc augmente
        mask_red = (df['delta_fc'] > 1) & (df['elevation_sol'] < 100)
        index_legend = 0
        for i in df['time_hm'][mask_red]:
            if index_legend == 0:
                ax1.axvline(x=i, color='red', alpha=1, label='Elevation sol < '+ str(optionsAnalyse[0]) +'m et FC montante')
            else:
                ax1.axvline(x=i, color='red', alpha=1)
            index_legend+=1

        # Ajouter des lignes verticales vertes quand fc stable ou descendante et vario < -2
        mask_green = (df['delta_fc'] <=1) & (df['elevation_sol'] < optionsAnalyse[0])
        index_legend = 0
        for i in df['time_hm'][mask_green]:
            if index_legend == 0:
                ax1.axvline(x=i, color='green', alpha=0.5, label='Elevation sol < '+ str(optionsAnalyse[0]) +'m et FC stable')
            else:
                ax1.axvline(x=i, color='green', alpha=0.5)
            index_legend+=1
            
        # Créer un deuxième axe des y pour la FC
        ax2 = ax1.twinx()
        ax2.plot(df['time_hm'], df['elevation_sol'], color='purple', label='Elevation sol (m)')
        
        ax2.axhline(y=optionsAnalyse[0], color='red', alpha=1, label='Seuil '+ str(optionsAnalyse[0]) +' m')

        # Titre du graphique
        plt.title('Elevation sol et variation FC dans le temps')

    # Ajout des légendes
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
                   


    # Enregistrer le graphique en tant que fichier image
    plt.savefig(outputDir + 'graph_' + type_analyse + '_' + time_gps_trace + '.png')

    # Afficher le graphique
    plt.show()
    
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpxFile", help="Chemin vers le fichier gpx")
    parser.add_argument("--outputDir", help="Chemin vers le dossier de sortie")
    parser.add_argument("--analyse", help="Choix du type de sortie du graph : vario ou altitude" , default='vario')
    parser.add_argument('--optionsAnalyse', type=str, help='Option : vario => [varioDescendant, varioAscendant], altitude => [seuil]', default='[-3,2]')
    parser.add_argument("--ecartPoint", help="Espacement des points dans le temps (60s, 10s ...)" , default='60s')
    args = parser.parse_args()
    optionsAnalyse = ast.literal_eval(args.optionsAnalyse)
    process_data(args.gpxFile, args.outputDir, args.analyse, optionsAnalyse, args.ecartPoint)



# exemple d'utilisation  : python flight_kpi.py --gpxFile "path\\to\\file\\vol.gpx" --outputDir "path\\to\\dir\\" --analyse "altitude" --optionsAnalyse "[100]" --ecartPoint "60s"
#process_data("dir\\vol2.gpx", "dir\\", "vario", [-3,2], "60s")