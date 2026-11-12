# Polices du rapport final pour ONLYOFFICE

Le modèle `backend/templates/rapport_template.pptx` utilise **Work Sans** (texte) et
**Rajdhani** (titres), deux polices sous licence SIL Open Font License.

Le Document Server ne connaît que les polices installées dans son conteneur : sans elles, il
affiche une police de substitution et la pagination peut différer.

1. Télécharger les fichiers `.ttf` (Google Fonts : Work Sans, Rajdhani) et les déposer ici.
2. Redémarrer le conteneur : `docker compose restart onlyoffice` (le cache des polices est
   régénéré au démarrage, `GENERATE_FONTS=true`).

Les `.ttf` / `.otf` de ce dossier ne sont pas versionnés (`.gitignore`).
