# Codec RLE pour les images binaires

Application Python avec interface graphique Tkinter permettant de dessiner une
image composée de pixels noirs (`0x00`) et blancs (`0xFF`), de la sauvegarder,
de l’encoder en RLE et de rouvrir une image compressée.

## Lancer

Python 3.10 ou supérieur est recommandé. Tkinter est généralement inclus avec
Python. Depuis ce dossier :

```sh
python3 main.py
```

Cliquez ou faites glisser le bouton gauche pour peindre en noir. Le bouton droit
peint en blanc. Les dimensions sont exprimées en pixels et limitées à 256 par
côté dans l’interface.

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
