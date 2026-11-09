# Phase 6 – Émission du rapport final : analyse et plan

> Statut : **plan à valider** (étapes 1 et 2). Aucun code n'a été écrit.
> Source analysée : `docs/phase6/rapport_exemple.pptx` (90 slides, 16:9, 33,87 × 19,05 cm), lu avec python-pptx 1.0.2 et rendu en images via LibreOffice.

---

## 1. Ce que l'exploration du code a établi

### 1.1 Données disponibles par phase (lecture seule pour la Phase 6)

| Phase | Collection / champ | Contenu exploitable dans le rapport |
|---|---|---|
| Mission | `missions` : `clientId`, `exercice`, `dateDebut`, `echeance`, `manager`, `senior` (noms en texte), `equipe` (ids d'employés), `cycleAssignments.{code}.assigneA`, `phase` (`"6/7 · Restitution client"`) | Exercice, équipe, rattachement client |
| Client | `clients` : `raisonSociale` \| `company_name`, `formeJuridique`, `rccm`, `compteContribuable`, `adresse`, `ville`… (2 schémas fusionnés par `serialize_client`) | Nom du client |
| 1 – Collecte | `missions.documents.categories[].documents[]` (fichiers dans `uploads/`) ; `missions.ficheSignaletique.valeurs` (27 rubriques : `denomination`, `sigle`, `formeJuridique`, `capitalSocial`, `anneeCreation`, `objet`, `gerant`, `associes`, `adresseGeographique`, `descriptionActivite`, `effectif`, `chiffreAffairesHT`…) | Présentation de l'entité |
| 2 – Contrôle | Calculés à la volée depuis les balances N / N-1 (`balance_service` → `balance_engine`) : `compute_intangibilite`, `compute_coherence`, `compute_vraisemblance` | Intangibilité du bilan, comptes par compte (ouverture, mouvements, clôture) |
| 3 – Organisation | `cycle_service.CYCLES` (13 cycles A–M, plages de comptes) ; `get_mission_cycle_detail` → comptes du cycle avec `soldeN` / `soldeNMoins1` | Extraits de balance par cycle |
| 4 – Révision | `cycle_revisions` (1 doc par mission × cycle) : `priseConnaissance{processus, risques[], referentiel}`, `lead.commentaires{compte: texte}`, `justification{assertions, pieces[], commentaire.texte}`, `constats[]{id, famille, constat, severite, recommandation, statut}`, `conclusion{synthese, ajustements[]{id, compte, libelle, sens, montant}, decision}` ; `working_papers` (PT par étape, `feuilles[]{nom, colonnes, data}` en mode intégré) | Constats, recommandations, sévérité, synthèses, écritures proposées, tableaux de cadrage (PT) |
| 5 – Revue | `cycle_revisions.statut` (`cloture` en fin de chaîne), `validations.{niveau}`, `review_points` | Prérequis à la génération. `sync_mission_phase` passe la mission en 6/7 quand **les 13 cycles** sont clôturés. |

Il n'y a **pas d'états financiers structurés** : le cycle M « États financiers » n'a aucune plage de comptes. Il n'y a **pas de grand livre** non plus : seules les balances sont importées.

### 1.2 Utilisateurs, rôles, affectations

- `employees.grade` porte les droits. `core/permissions.py` définit deux choses : `is_management_grade` (Senior et au-dessus) et `review_rank` (Senior / Assistant Manager = 1, Manager / Senior Manager = 2, Associé = 3).
- Il existe deux affectations : `missions.equipe` (liste d'ids, Phase 3) et `missions.cycleAssignments.{code}.assigneA` (un collaborateur par cycle). `manager` et `senior` ne sont que des **noms** en texte, sans id.
- Auth : JWT HS256 (`JWT_SECRET_KEY`, 8 h). `get_current_employee` relit l'employé en base à chaque requête.

### 1.3 Intégration front d'une phase

- `MissionWorkspaceModal.vue` contient la table `phaseGroups`. La Phase 6 y est **déjà déclarée** avec les sous-étapes `restitution-client` et `emission-rapport-final`. Faute d'entrée dans `stepComponents`, elles affichent `EnDeveloppement.vue`.
- Chaque étape reçoit les props `mission` et `client`. Les appels passent par `apiFetch` (`composables/useCycleRevision.js`) ou par un `fetch` local.
- Couleurs : navy `#0d3b56`, teal `#2c6e8f`, amber `#c9862c` / `#fbeee0`, vert `#7cb342` / `#eef6e6`. Cartes `rounded-xl bg-white p-5 shadow-sm`.

---

## 2. Analyse de `rapport_exemple.pptx`

### 2.1 Masques et dispositions : **pas de vrai masque exploitable**

| Masque | Dispositions | Slides qui l'utilisent | Constat |
|---|---|---|---|
| m0 | 46 dispositions **« Deloitte »** (`Divider - Deloitte green`, `Key statement…`, `Team profile`…) | 4 (sommaires 10, 11, 59, 89, disposition `Title Only`) | Modèle d'un autre cabinet, à **ne pas réutiliser** (marque tierce) |
| m1 | 12 dispositions Office FR standard (`Diapositive de titre`, `Vide`, `Titre et contenu`…) | 85 | 81 slides sur `Diapositive de titre`, mais **aucun placeholder utilisé** |
| m2 | 1 disposition | 1 (couverture) | — |

- **Toute la mise en forme est faite slide par slide** : zones de texte libres (`ZoneTexte 4` répétée), bandeau de pied et logo Y3 recopiés, pastilles de numéro de partie dessinées à la main.
- Aucune slide n'a de placeholder vide, mais c'est parce qu'aucune n'en utilise.
- Il n'y a **aucun graphique natif**. On trouve en revanche **18 objets OLE `Excel.Sheet.12`** (feuilles Excel incrustées, affichées comme icône ou image) sur les slides 12, 15, 17, 19, 22, 24, 28, 37, 43, 53, 56, 61, 64, 69 (×2), 72, 81 et 87.
- Images : logo du client (couverture et séparateur), photo du siège du client (slide 2), logos Y3 et visuel de l'adresse (slide 90).
- Polices : **Work Sans** (corps) et **Rajdhani Bold** (titres), Calibri et Wingdings (puces). Couleurs : navy `#043D5D` / `#073E5D` et vert Y3 `#92D050`.

### 2.2 Incohérences relevées dans l'exemple (à confirmer, cf. questions)

- Le sommaire annonce une partie **3 « Travaux de régularisation »** (3.1 récapitulatif des écritures, 3.2 nouvelle balance, 3.3 variation du résultat), ainsi que 2.8 « Revenus financiers » et 2.9 « Autres produits ». **Ces sections sont absentes du document**, qui s'arrête à 2.7.
- La numérotation du sommaire ne suit pas celle des slides : le sommaire donne 1.3 Immobilisations / 1.4 Stocks, les slides donnent 1.3 PIDR / 1.4 Immobilisations, et il n'y a pas de slide Stocks.
- La couverture contient un texte masqué périmé (« Mai 2024 » sous « Avril 2026 »).

### 2.3 Types de slides identifiés

| Code | Type | Slides de l'exemple |
|---|---|---|
| T1 | Couverture | 1 |
| T2 | Séparateur de partie (photo + n° + titre) | 2 |
| T3 | Texte titré (contexte, présentation, évènements) | 3, 4, 5 |
| T4 | Contrôle interne – introduction et légende des priorités | 6 |
| T5 | Contrôle interne – fiche constat (tableau 5 colonnes + feu de priorité) | 7, 8, 9 |
| T6 | Sommaire (3 parties, partie courante surlignée) | 10, 11, 59, 89 |
| T7 | Intangibilité du bilan | 12 |
| T8 | Rubrique de cycle (en-tête partie, n° rubrique, texte, 0 à 3 tableaux, commentaires client / cabinet) | 13–58, 60–88 (75 slides) |
| T9 | Travaux de régularisation (annoncés, absents) | — |
| T10 | Fin (adresse du cabinet) | 90 |

Dans une rubrique T8, on trouve ces **blocs** :
- **B1** extrait de balance (compte, intitulé, solde) ;
- **B2** tableau de variation (solde d'ouverture, diminution, augmentation, solde de clôture) ;
- **B3** texte d'analyse ;
- **B4** tableau de cadrage ou de rapprochement (mensuel, comptabilité vs déclaration ou livre de paie) ;
- **B5** extrait du grand livre ;
- **B6** écriture proposée (compte, libellé, débit, crédit) ;
- **B7** « Commentaire [client] » et « Commentaire Y3 » ;
- **B8** objet Excel incrusté.

---

## 3. Mapping slide → type → source

Légende : **S** = statique, **D** = dynamique, **M** = manuelle (aucune source aujourd'hui).

| Slides exemple | Type | Élément | Cat. | Source exacte |
|---|---|---|---|---|
| 1 | T1 Couverture | « Révision des comptes », « Confidentiel », logos Y3 | S | Modèle |
| | | « Exercice 2025 » | D | `missions.exercice` |
| | | Date du rapport (« Avril 2026 ») | M | **manquant** → `rapports.saisie.dateRapport` (proposé : mois de génération par défaut, modifiable) |
| | | Logo du client | M | **manquant** → fichier déposé en Phase 6 (GridFS) |
| 2 | T2 Séparateur | N° et titre de partie | S | Structure du rapport |
| | | Photo et logo du client | M | **manquant** → dépôt Phase 6, sinon visuel neutre du cabinet |
| 3 | T3 Contexte et objectifs | Paragraphes de cadrage (SYSCOHADA, CGI, code du travail, réserves d'usage, diligences OHADA) | S | Texte type du cabinet, dans le modèle |
| | | Nom du client | D | `clients.raisonSociale` (ou `ficheSignaletique.valeurs.denomination` si renseignée) |
| | | Exercice | D | `missions.exercice` |
| | | Date de la lettre de mission, nature des prestations | M | **manquant** → `rapports.saisie.lettreMission{date, prestations}` |
| | | Phrase spécifique au client (« holding regroupant… ») | M | **manquant** → `rapports.saisie.contexteComplement` |
| 4 | T3 Présentation de l'entité | Forme juridique, capital, année de création, siège, activité, représentant | D | `missions.ficheSignaletique.valeurs.{denomination, formeJuridique, capitalSocial, anneeCreation, adresseGeographique, objet \| descriptionActivite, gerant}`, insérés dans des **phrases-gabarits fixes**. Une rubrique vide fait disparaître sa phrase. Aucune reformulation. |
| | | Actionnariat | D / M | `ficheSignaletique.valeurs.associes` (une ligne par associé). Le nombre d'actions et la valeur nominale sont **manquants** et passent par une saisie libre. |
| 5 | T3 Évènements significatifs | Titre et texte de chaque évènement | M | **manquant** → `rapports.saisie.evenements[]{titre, texte}`. Slide omise si la liste est vide. |
| 6 | T4 CI introduction | Définition du contrôle interne, légende des 3 priorités | S | Modèle |
| | | Liste des points relevés | D | Titres des constats retenus pour le CI (ligne suivante) |
| 7–9 | T5 Fiche constat CI (**1 slide par constat retenu**, paginée si le texte déborde) | Titre « Trésorerie : … » | D / M | Libellé du cycle (`CYCLES[code].libelle`) + **titre court manquant** → `rapports.saisie.constats[constatId].titre` |
| | | Constat / Observation | D | `cycle_revisions.constats[].constat` |
| | | Risques | M | **manquant** → `rapports.saisie.constats[constatId].risques[]`. (`priseConnaissance.risques` existe, mais au niveau du cycle et pas du constat. Il peut servir de suggestion à cocher.) |
| | | Recommandations Y3 | D | `cycle_revisions.constats[].recommandation` |
| | | Commentaires du management | M | **manquant** → alimenté par la sous-étape *Restitution client* (cf. questions) |
| | | Priorité (feu rouge / orange / vert) | D | `cycle_revisions.constats[].severite` : Élevé → forte, Moyen → moyenne, Faible → faible |
| 10, 11, 59, 89 | T6 Sommaire | Parties et rubriques, partie courante surlignée | D (structurel) | Liste des chapitres **réellement générés**. Le sommaire ne peut donc plus annoncer une section absente. |
| 12 | T7 Intangibilité | Tableau des comptes en écart (N-1 clôture vs N ouverture) | D | `balance_service.get_controle_intangibilite` → `ecarts`, `comptes[]` (balances `missions.documents`). Remplace l'objet Excel. |
| | | Phrase de constat | D | Phrase-gabarit selon le résultat calculé (« X comptes présentent un écart… » / « respecté ») |
| | | Analyse et demande de correction | M | **manquant** → `rapports.saisie.intangibilite.commentaire` |
| 13–58, 60–88 | T8 Rubrique de cycle | En-tête « Comptes de bilan / gestion », n° et libellé de rubrique | S / D | Structure (cf. question Q1) + `CYCLES[code].libelle` |
| (16, 22, 28, 38, 67, 68, 71, 87) | B1 Extrait de balance | Compte, intitulé, solde N (+ N-1, variation), total | D | `cycle_service.get_mission_cycle_detail(mission, code)` → `comptes[]{numero, libelle, soldeN, soldeNMoins1}`. Filtrable par préfixes. **Paginé.** |
| | | Commentaire par compte | D | `cycle_revisions.lead.commentaires[numero]` |
| (13) | B2 Tableau de variation | Ouverture, diminution, augmentation, clôture | D | Balance N parsée (`parse_balance_file` : `debit/creditOuverture`, `debit/creditMouvement`, `debit/creditCloture`) |
| (toutes) | B3 Texte d'analyse | Synthèse du cycle | D | `cycle_revisions.conclusion.synthese` (texte saisi en 4f, repris **tel quel**) |
| | | Commentaire de justification | D | `cycle_revisions.justification.commentaire.texte` |
| | | Texte propre à chaque sous-point (« Fournisseurs anormalement débiteurs… ») | M | **manquant** : le rapport a N sous-points par cycle, EC Perform 1 synthèse par cycle → `rapports.saisie.points[]` (§ 4) |
| (17, 33–36, 39–42, 45–51, 78, 80, 84, 85) | B4 Cadrage / rapprochement | Tableaux mensuels | D si désigné | `working_papers.feuilles[]` (PT en mode intégré). L'utilisateur choisit la feuille et éventuellement la plage dans le point du rapport. **Paginé.** PT en mode « lien » : copie `.xlsx` importée, si elle existe. |
| (25, 27, 31, 32, 44, 54, 55, 58, 60, 62, 64–66, 73, 75, 77, 79, 81–83, 86, 88) | B5 Extrait du grand livre | Lignes d'écritures | M | **manquant** : pas de grand livre dans EC Perform. Proposé en V1 : coller l'extrait dans une feuille de PT, puis le désigner comme un B4. Sinon, ajout dans ONLYOFFICE. |
| (15, 18, 19, 23, 26, 37, 40, 41, 48, 51, 60–70, 72, 74–78, 80, 82, 88) | B6 Écriture proposée | Compte, libellé, débit, crédit | D | `cycle_revisions.conclusion.ajustements[]{compte, libelle, sens, montant}` |
| | | Regroupement des lignes en écritures équilibrées | M | **manquant** : un ajustement n'est qu'une ligne → `rapports.saisie.points[].ajustementIds[]` (contrôle débit = crédit à l'enregistrement) |
| (12, 13, 60–75, 86) | B7 Commentaires client / cabinet | « Commentaire KDA » / « Commentaire Y3 » | M | **manquant** → Restitution client (cf. questions) |
| (18 slides) | B8 Objets Excel OLE | — | — | **Non reproduits.** Remplacés par des tableaux natifs (B1, B4) ou, à défaut, ajoutés dans ONLYOFFICE. |
| *(absent)* | T9 3.1 Récapitulatif des écritures | Toutes les écritures proposées | D | Tous les `cycle_revisions.conclusion.ajustements[]` de la mission, **paginés** |
| *(absent)* | T9 3.2 Nouvelle balance attendue | Balance N corrigée | D | Balance N + ajustements (calcul pur, sans saisie) |
| *(absent)* | T9 3.3 Variation du résultat | Impact des ajustements sur le résultat | D | Somme des ajustements sur les classes 6, 7 et 8 |
| 90 | T10 Fin | Adresse du cabinet | S | Modèle |

### Volume estimé pour une mission type

Slides fixes (T1, T2 ×3, T3 ×3, T4, T6 ×4, T7, T10) : environ 14. S'y ajoutent 1 slide par constat CI retenu, au moins 1 slide par cycle non vide, plus les pages des tableaux paginés et les slides de régularisation. Pour une mission complète, on retombe sur **90 à 120 slides**, comme demandé. Le test fixe un nombre exact, calculé à partir des données de démonstration.

---

## 4. Données manquantes et proposition de saisie

Toutes les données manquantes restent **dans la Phase 6**, sans toucher aux modèles des phases 1 à 5. Elles sont stockées dans `rapports.saisie`, avec un verrouillage optimiste (`version`), comme pour `cycle_revisions`. Elles sont rattachées aux objets existants par leur id (`constatId`, `ajustementId`, `paperId`).

| # | Donnée | Saisie proposée | Pré-remplissage (copie, jamais de reformulation) |
|---|---|---|---|
| M1 | Date du rapport | Champ mois / année | Mois de génération |
| M2 | Lettre de mission : date et prestations | Date + texte court | — |
| M3 | Logo et photo du client | Dépôt d'image (PNG / JPG) | — |
| M4 | Complément au contexte | Texte libre (facultatif) | — |
| M5 | Évènements significatifs | Liste titre + texte | — |
| M6 | Actionnariat détaillé | Texte libre | `ficheSignaletique.associes` |
| M7 | Constat → contrôle interne | Case « Retenir pour le CI », titre court, liste de risques | Case cochée pour les familles *Gouvernance* et *Système d'information* (à confirmer, Q2) ; risques proposés à partir de `priseConnaissance.risques` |
| M8 | Points du rapport par cycle | Liste ordonnée : titre, texte, blocs à insérer (extrait de balance avec préfixes, feuille / plage de PT, écritures) | Un point « Synthèse » par cycle avec `conclusion.synthese` et l'extrait de balance du cycle |
| M9 | Regroupement des écritures | Sélection d'ajustements dans un point, avec contrôle débit = crédit | — |
| M10 | Commentaire sur l'intangibilité | Texte libre | — |
| M11 | Commentaires client / management | **Restitution client** (Q10) | — |

**Écran de saisie** : un panneau « Préparation du rapport » dans la sous-étape *Émission du rapport final*, avec 4 onglets (Généralités, Contrôle interne, Points par cycle, Écritures). Tout ce qui n'est pas saisi est **omis**, jamais remplacé par un texte par défaut. Le reste se finalise dans ONLYOFFICE.

---

## 5. Modèle PowerPoint : proposition

**Je ne recommande pas de réutiliser le masque existant.** Trois raisons :
- il ne contient aucune disposition réellement employée ;
- le masque m0 est un modèle Deloitte ;
- la mise en forme est entièrement manuelle, donc il n'y a aucun placeholder à remplir.

**Proposition** : construire `backend/templates/rapport_template.pptx`, avec **un seul masque à l'identité Y3**. Il reprend les éléments déjà présents dans l'exemple : navy `#043D5D`, vert `#92D050`, Work Sans / Rajdhani, bandeau de pied navy avec logo Y3 et numéro de slide. Le modèle comporte **une disposition nommée par type** :

| Disposition | Placeholders (idx → usage) |
|---|---|
| `EC Couverture` | 0 titre, 1 exercice, 10 date, 11 image client |
| `EC Séparateur` | 0 titre de partie, 10 numéro, 11 image |
| `EC Sommaire` | 0 titre, 1 corps (3 colonnes générées) |
| `EC Texte` | 0 titre, 13 rubrique, 1 corps |
| `EC Tableau` | 0 titre, 13 rubrique, 12 tableau (placeholder de type `tbl` : `insert_table` conserve la position et la taille) |
| `EC Texte + tableau` | 0 titre, 13 rubrique, 1 corps (haut), 12 tableau (bas) |
| `EC Constat CI` | 0 titre, 13 rubrique, 12 tableau 5 colonnes, 14 feu de priorité |
| `EC Fin` | aucun (contenu statique) |

- **Construction** : un script versionné, `backend/scripts/construire_modele.py`, part de l'exemple. Il garde le thème, les polices et les logos Y3, et supprime les masques m0 / m2, toutes les slides et toute donnée KDA. Il génère ensuite les dispositions ci-dessus en XML. Le cabinet pourra retoucher le visuel dans PowerPoint, à condition de **conserver les noms des dispositions et les idx**, sur lesquels s'appuient les builders.
- **Règle des builders** : tout placeholder non rempli est **supprimé** de la slide, jamais laissé vide. Un test le vérifie, ainsi que l'absence de « Cliquez pour… ».
- **Pagination** : nombre de lignes par slide calculé d'après la hauteur du placeholder et la taille de police. En-tête répété, suffixe « (1/3) » dans le titre, total uniquement sur la dernière page.
- **ONLYOFFICE** : Work Sans et Rajdhani (licence OFL) doivent être installées dans le conteneur, sinon le rendu diffère. Je prévois un volume de polices et la commande `documentserver-generate-allfonts.sh`.

---

## 6. Architecture technique prévue (étape 3)

### 6.1 Backend

```
app/
  models/rapport.py              # Pydantic : SaisieRapport, GenererRequest(force), …
  routers/rapports.py            # /missions/{id}/rapport/...
  routers/onlyoffice.py          # /onlyoffice/fichier, /onlyoffice/callback (sans bearer : JWT ONLYOFFICE)
  services/rapport_service.py    # statut, versions, droits, règles (régénération, émission), GridFS
  services/onlyoffice_service.py # config signée, vérif. JWT, téléchargement callback, conversion PDF
  services/rapport/
    donnees.py                   # collecte en LECTURE SEULE des phases 1-5 → dict « RapportData »
    builders.py                  # 1 fonction par type : couverture, separateur, texte, sommaire,
                                 #   intangibilite, constat_ci, extrait_balance, variation, tableau_pt,
                                 #   ecritures, recap_ecritures, balance_corrigee, variation_resultat, fin
    pagination.py                # découpage des tableaux / textes trop longs
    assembleur.py                # orchestre l'ordre des chapitres et le sommaire, retourne les octets PPTX
templates/rapport_template.pptx
scripts/construire_modele.py
```

- `donnees.py` est la seule couche qui lit Mongo. Les builders sont **purs** (`Presentation` + données → slides), donc testables sans base.
- **Montants** : `format_montant` existant, au format FCFA « 1 234 567 ». Négatifs en « - 1 234 ».
- **Collection `rapports`**, une par mission (index unique `missionId`) :
  ```
  { missionId, statut: "genere"|"en_finition"|"emis", compteurVersion,
    versions: [{ numero, date, auteur{id,nom,grade}, origine: "generation"|"edition_onlyoffice"|"emission",
                 fileId, cle, taille, basee_sur }],
    pdfFileId, emisLe, emisPar, saisie{…}, saisieVersion, sessionsOuvertes: [cle] }
  ```
  Fichiers dans le bucket GridFS `rapports` (métadonnées `missionId`, `numero`). Le numéro de version est attribué atomiquement (`find_one_and_update` + `$inc`).
- **Endpoints** :

  | Méthode | Route | Rôle |
  |---|---|---|
  | GET | `/missions/{id}/rapport` | État, versions, droits de l'utilisateur, avertissement de régénération |
  | PUT | `/missions/{id}/rapport/saisie` | Données manquantes (§ 4), avec version |
  | POST | `/missions/{id}/rapport/medias` | Logo et photo du client |
  | POST | `/missions/{id}/rapport/generer?force=false` | Génération / régénération. **409** si une version `edition_onlyoffice` existe et que `force` n'est pas posé, ou si une session d'édition est ouverte |
  | GET | `/missions/{id}/rapport/versions/{n}/fichier` | Téléchargement (bearer) |
  | GET | `/missions/{id}/rapport/editeur?version=` | Config `DocsAPI.DocEditor` signée HS256 avec `ONLYOFFICE_JWT_SECRET` (`document.key = {rapportId}-v{n}`, `mode` edit / view, `user{id, name}`, `callbackUrl`) |
  | GET | `/onlyoffice/fichier/{jeton}` | Fichier servi au Document Server (jeton court signé, et JWT ONLYOFFICE vérifié dans l'en-tête) |
  | POST | `/onlyoffice/callback` | JWT vérifié. Statuts 2 et 6 : téléchargement de `url`, puis nouvelle version `edition_onlyoffice`, statut `en_finition`. Statuts 1 / 4 : suivi des sessions ouvertes. Réponse `{"error": 0}`. |
  | POST | `/missions/{id}/rapport/emettre` | Fige la dernière version (copie `emission`), statut `emis`, puis conversion PDF via `ConvertService.ashx` (pdf stocké dans GridFS). Ensuite : config toujours en `view`, callbacks et régénération refusés. |
  | GET | `/missions/{id}/rapport/pdf` | PDF émis |

- **Droits proposés** (cf. Q3) :
  - éditer = membre de `missions.equipe` **ou** grade d'encadrement, et rapport non émis ;
  - générer = grade d'encadrement ;
  - émettre = Associé (rang 3) ;
  - tous les autres = lecture seule.

  Chaque écriture est revérifiée côté serveur.
- **Prérequis de génération** (cf. Q4) : mission en 6/7, donc 13 cycles clôturés. Sinon 409.

### 6.2 Infrastructure

- Il n'y a **pas de `docker-compose.yml` aujourd'hui** : Mongo et le backend tournent dans WSL, et Docker Desktop est installé. Je propose un `docker-compose.yml` à la racine avec **seulement** `onlyoffice/documentserver` (version figée, `JWT_ENABLED=true`, `JWT_SECRET=${ONLYOFFICE_JWT_SECRET}`, port 8080, volumes données / logs / polices).
- **Variables** (dans `backend/.env.example`, créé, et `frontend/.env.example`) :
  - `ONLYOFFICE_JWT_SECRET` ;
  - `ONLYOFFICE_PUBLIC_URL` : navigateur → DS, `http://localhost:8080` ;
  - `ONLYOFFICE_INTERNAL_URL` : backend → DS, pour la conversion ;
  - `BACKEND_URL_FOR_ONLYOFFICE` : DS → backend, `http://host.docker.internal:8000`, pour le téléchargement et le callback ;
  - `VITE_ONLYOFFICE_URL`.

  Le backend écoute déjà sur `::`. L'appel du conteneur vers le uvicorn de WSL via `host.docker.internal` reste **à vérifier** sur ce poste.
- `app/main.py` : CORS inchangé. Les routes `/onlyoffice/*` sont appelées de serveur à serveur.
- ONLYOFFICE Docs **Community** : licence AGPL v3, **20 connexions simultanées** au maximum. C'est suffisant pour un cabinet, mais à connaître.

### 6.3 Frontend

- `components/mission-steps/EmissionRapport.vue`, branché dans `stepComponents['emission-rapport-final']`. Il contient :
  - une carte de statut (badge Généré / En finition / Émis) ;
  - le bouton Générer / Régénérer, avec une modale d'avertissement explicite quand des modifications ONLYOFFICE existent, puis un nouvel appel avec `force=true` ;
  - la liste des versions (n°, date, auteur, origine, téléchargement) ;
  - le bouton « Ouvrir dans l'éditeur » ;
  - le bouton « Émettre le rapport final », avec une confirmation qui rappelle que l'action est irréversible ;
  - le panneau « Préparation du rapport » (§ 4).
- `components/rapport/EditeurOnlyoffice.vue` : charge `${VITE_ONLYOFFICE_URL}/web-apps/apps/api/documents/api.js` une seule fois, instancie `new DocsAPI.DocEditor(id, config)` avec la config du backend, et appelle `destroyEditor()` au démontage. Il s'affiche en plein écran dans la modale de mission.

### 6.4 Vérification (étape 4)

- `tests/test_rapport.py` crée la mission de démonstration **SAVEDO SA**, déjà utilisée par `conftest.py` : balances N / N-1 générées avec openpyxl, 13 cycles clôturés avec constats, synthèses et ajustements, plus une saisie Phase 6. Le test vérifie le nombre exact de slides, l'absence de placeholder vide et de « Cliquez pour », et la présence des montants attendus au format FCFA.
- Tests d'API : régénération bloquée puis autorisée avec `force` ; callback avec un JWT invalide refusé ; callback 2 / 6 qui crée une version (téléchargement simulé) ; émission qui fige le rapport.
- Comparaison visuelle : LibreOffice est **disponible dans WSL** (`soffice`, `pdftoppm`). Le rapport généré et l'exemple sont rendus en PNG, sur quelques slides clés.
- Cycle complet avec un vrai Document Server dans Docker : génération → éditeur → modification → callback → v2 → émission.

---

## 7. Questions

**Structure et contenu**

- **Q1 — Plan du rapport.** L'exemple est organisé par **rubriques comptables** (1 Comptes de bilan / 2 Comptes de gestion / 3 Régularisations), et non par cycle A–M. Or les cycles B, C, F et G couvrent à la fois du bilan et de la gestion (ex. C = fournisseurs 40 + achats 60). Deux options :
  - (a) **un chapitre par cycle A–M** : c'est la structure des données, et chaque synthèse et chaque écriture tombe naturellement à sa place ;
  - (b) la structure bilan / gestion de l'exemple : chaque cycle mixte est découpé en deux, et ses points de rapport sont classés à la main.

  Je recommande (a) pour la V1, avec une table d'ordre et de libellé des chapitres configurable. **Quelle option préférez-vous ?**
- **Q2 — Contrôle interne.** Quels constats vont dans la partie CI ? Je propose : la case « Retenir pour le CI », cochée par défaut pour *Gouvernance* et *Système d'information*. Les autres constats apparaissent dans leur rubrique de cycle.
- **Q3 — Droits.** Qui peut **émettre** ? Je propose l'Associé seul. Qui peut **éditer** dans ONLYOFFICE : toute l'équipe de la mission plus l'encadrement, ou seulement l'encadrement ?
- **Q4 — Prérequis.** La génération est-elle réservée aux missions en Phase 6 (13 cycles clôturés) ? Ou faut-il permettre un brouillon plus tôt, marqué « Projet » ?
- **Q5 — Modèle.** Validez-vous la construction d'un modèle propre par script, sans les éléments Deloitte ? Qui, au cabinet, validera le visuel ?
- **Q6 — Extraits du grand livre** (environ 25 slides de l'exemple). La V1 peut les reprendre depuis une feuille de PT désignée, ou bien ils sont ajoutés dans ONLYOFFICE. Faut-il prévoir l'import du grand livre (Phase 1) dans une version ultérieure ?
- **Q7 — Partie 3 « Travaux de régularisation ».** Je la génère (récapitulatif des écritures, balance corrigée, variation du résultat), alors qu'elle n'est qu'annoncée dans l'exemple. D'accord ?
- **Q8 — Équipe et états financiers.** Faut-il une slide « Équipe de la mission », absente de l'exemple ? Pour les états financiers : rien dans la V1, faute de données structurées ?
- **Q9 — PDF.** Faut-il l'export PDF à l'émission (via ONLYOFFICE) dès la V1 ?

**Infrastructure**

- **Q10 — Docker.** Le compose ne contient-il que le Document Server, Mongo et le backend restant dans WSL ? Ou faut-il conteneuriser aussi le backend et Mongo ? Le poste de déploiement final est-il celui-ci ?

**Sous-étape « Restitution client »**

- **Q11 — Nature.** Est-ce la réunion de présentation du **projet de rapport** au client, avant l'émission ?
- **Q12 — Commentaires du client.** Les « Commentaires du management » des fiches CI et les « Commentaire KDA / Commentaire Y3 » des rubriques sont-ils recueillis pendant la restitution ? Si oui, doivent-ils être saisis **dans EC Perform**, par constat et par point (puis réinjectés à la génération), ou directement dans le PPTX via ONLYOFFICE ?
- **Q13 — Traçabilité.** Faut-il enregistrer la date, les participants (cabinet et client), un compte rendu ou un PV signé (dépôt de fichier) ?
- **Q14 — Version envoyée.** La restitution s'appuie-t-elle sur une version précise du rapport, à tracer comme « version provisoire envoyée au client » ? Peut-il y avoir plusieurs allers-retours ?
- **Q15 — Enchaînement.** La restitution est-elle un **prérequis à l'émission** (bouton « Émettre » bloqué tant qu'elle n'est pas validée) ? Qui la valide ? L'émission fait-elle passer la mission en Phase 7 (Archivage) ?
- **Q16 — Accès du client.** Le client doit-il avoir un accès à EC Perform ? Je suppose que non : il n'existe aujourd'hui aucun compte externe.

**Confidentialité**

- **Q17.** `rapport_exemple.pptx` contient un **dossier client réel** (KOFFI & DIABATE ARCHITECTES : chiffres, noms de salariés, comptes bancaires). Le dossier `docs/` n'est pas suivi par git. Je propose d'ajouter `docs/phase6/*.pptx` au `.gitignore`, de ne jamais l'utiliser comme jeu de test (les tests utilisent SAVEDO SA, fictif) et de ne pas l'embarquer dans le modèle. D'accord ?
