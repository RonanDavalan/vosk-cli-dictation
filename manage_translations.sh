#!/bin/bash

# ==============================================================================
# compile_translations.sh
#
# Ce script compile les fichiers de traduction .po en fichiers .mo binaires
# que Python peut utiliser. Il doit être exécuté depuis la racine du projet.
#
# Il automatise :
#   - La vérification des chemins nécessaires (locales, venv).
#   - L'activation de l'environnement virtuel.
#   - L'exécution de la commande de compilation Babel.
# ==============================================================================

# --- Couleurs pour les messages ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Configuration ---
# Le nom du dossier de l'environnement virtuel
VENV_DIR="vosk-env"
# Le nom du dossier contenant les traductions
LOCALES_DIR="locales"

# Se placer dans le répertoire où se trouve le script pour s'assurer
# que les chemins relatifs sont corrects.
cd "$(dirname "$0")" || exit

echo -e "${YELLOW}--- Compilation des traductions pour le projet Vosk ---${NC}"

# --- Vérification 1 : Le dossier 'locales' existe-t-il ? ---
if [ ! -d "$LOCALES_DIR" ]; then
    echo -e "${RED}ERREUR : Le dossier '$LOCALES_DIR' n'a pas été trouvé.${NC}"
    echo "Ce script doit être à la racine du projet."
    exit 1
fi
echo "[1/4] Le dossier '$LOCALES_DIR' a été trouvé."

# --- Vérification 2 : L'environnement virtuel existe-t-il ? ---
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}ERREUR : L'environnement virtuel '$VENV_DIR' est introuvable.${NC}"
    echo "Veuillez d'abord créer l'environnement avec 'python -m venv $VENV_DIR'."
    exit 1
fi
echo "[2/4] L'environnement virtuel '$VENV_DIR' a été trouvé."

# --- Étape 3 : Activer l'environnement virtuel ---
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "[3/4] Environnement virtuel activé."

# --- Vérification 3 : La commande 'pybabel' est-elle disponible ? ---
if ! command -v pybabel &> /dev/null; then
    echo -e "${RED}ERREUR : La commande 'pybabel' n'a pas été trouvée après activation du venv.${NC}"
    echo "Assurez-vous que Babel est bien installé dans votre venv ('pip install Babel')."
    exit 1
fi

# --- Étape 4 : Lancer la compilation ---
echo "[4/4] Lancement de la compilation des fichiers .po en .mo..."
pybabel compile -d "$LOCALES_DIR"

# Vérifier le code de sortie de la commande précédente
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}SUCCÈS : Les fichiers de traduction ont été compilés avec succès !${NC}"
else
    echo -e "\n${RED}ÉCHEC : Une erreur est survenue lors de la compilation.${NC}"
    exit 1
fi

exit 0
