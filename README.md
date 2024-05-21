Analyse de la FC sur des kpis de vol

Certaines montres permettent de récupérer la fréquence cardiaque (FC) dans la balise optionnelle hr (heart rate) d'un fichier GPX.
Dans un vol en parapente la fréquence cardiaque évolue. Les hypothèses d'analyse sont les suivantes :
- la FC est impactée par des variations de l'altitude importante (vario positif ou négatif) => analyse 'vario'
- la FC est impactée par la proximité du relief => analyse 'altitude'

Le script prend en paramètre un fichier gpx qui comporte la balise hr en plus des infos standards (latitude, longitude, altitude par rapport au niveau de la mer).
Plusieurs infos en sont déduites :
- variation altitude dans le temps (vario GPS et non barométrique)
- altitude sol
- variation FC

Le script produit de base :
- 1 fichier csv brut avec toutes les informations récupérées du fichier gpx et enrichies des inforations déduites
- 1 fichier image selon l'axe d'analyse choisi : 'vario' ou 'altitude'

Liste des paramètres à renseigner au lancement du script :
- --gpxFile : Chemin vers le fichier gpx 
- --outputDir : Chemin vers le dossier de sortie
- --analyse : Choix du type de sortie du graph : vario ou altitude 
- --optionsAnalyse: tableau de paramètre : vario => [varioDescendant (float), varioAscendant  (float) ], altitude => [seuil  (float), '>'['<']
- --ecartPoint Espacement des points dans le temps exemple : 1min, 10s ...

exemples d'utilisation  : 

python flight_kpi.py --gpxFile "path\\to\\file\\vol.gpx" --outputDir "path\\to\\dir\\" --analyse "vario" --optionsAnalyse "[-3,2]" --ecartPoint "30s"
python flight_kpi.py --gpxFile "path\\to\\file\\vol.gpx" --outputDir "path\\to\\dir\\" --analyse "altitude" --optionsAnalyse "[100]" --ecartPoint "1min"
