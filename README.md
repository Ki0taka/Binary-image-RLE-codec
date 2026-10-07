# Codec RLE pour les images binaires

Application Python avec interface graphique Tkinter et traitement d’images
OpenCV. Elle permet de dessiner une image composée de pixels noirs (`0x00`) et
blancs (`0xFF`), d’ouvrir ou exporter des images PNG, de sauvegarder l’image,
de l’encoder en RLE et de rouvrir une image compressée. Une fenêtre affiche les
étapes et les champs binaires de chaque paquet RLE.

## Lancer

Python 3.10 ou supérieur est recommandé. Tkinter est généralement inclus avec
Python. Installez OpenCV et NumPy, puis lancez l’application :

```sh
python3 -m pip install -r requirements.txt
python3 main.py
```

Sur Ubuntu/Debian, si l’import `tkinter` échoue, installez aussi le paquet
système `python3-tk`.

Cliquez ou faites glisser le bouton gauche pour peindre en noir. Le bouton droit
peint en blanc. Les dimensions sont exprimées en pixels et limitées à 256 par
côté dans l’interface.
Les dimensions saisies ne deviennent actives qu’après avoir cliqué sur
« Nouvelle image ». Les imports PNG, JPEG et BMP plus grands sont réduits pour
tenir dans la limite de 256 pixels par côté; les fichiers `.bimg` et `.rle`
plus grands sont refusés avec un message explicatif.

Pour commencer à partir d’une image existante, ouvrez un PNG, JPEG ou BMP :
OpenCV le convertit en niveaux de gris puis le seuillage le transforme en
pixels noirs ou blancs. « Exporter PNG » enregistre le dessin courant comme
image standard.

« Étapes de compression » explique les paquets sans créer de fichier. La
compression avec sauvegarde affiche aussi les paquets effectivement écrits.
« Décompresser / ouvrir » affiche chaque paquet lu, son en-tête, sa longueur et
les pixels qu’il ajoute à l’image.

Dans l’éditeur, le clic gauche peint en noir et le clic droit peint en blanc.

## Format RLE

Chaque paquet commence par un mot de 16 bits en ordre réseau (big-endian). Son
bit de poids fort indique le type : `1` pour une répétition, `0` pour une suite
littérale. Les 15 bits restants donnent le nombre de pixels. Un paquet de
répétition est suivi d’un octet couleur; un paquet littéral est suivi des octets
de pixels. Les répétitions de trois pixels ou plus sont encodées en paquet de
répétition; les autres pixels sont regroupés en paquets littéraux.

Les fichiers `.bimg` et `.rle` ont un en-tête de 12 octets : signature (`BIMG`
ou `RLE1`), largeur et hauteur en entiers non signés big-endian de 32 bits. Le
corps d’un `.bimg` contient les pixels directement; celui d’un `.rle` contient
le flux encodé ci-dessus.
