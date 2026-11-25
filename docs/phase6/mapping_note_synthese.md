# Phase 6 – Note de synthèse de fin de mission : mapping et plan

> Statut : **à valider**. Aucun code n'a été écrit.
> Remplace `mapping_rapport.md` (rapport de 90 slides, abandonné).
> Modèle analysé : `docs/phase6/Y3_EC_Note_de_synthese_modele_v1.pptx`, 13 slides 16:9 (10 × 5,625 po), toutes sur la
> disposition « Vide ». Les zones à compléter sont en rouge `#D0021B`, entre crochets. Couleur du texte normal : `#1A2535`
> (corps) ou la couleur non rouge déjà présente dans la même zone (`#FFFFFF` sur la couverture, `#00609C` pour les
> variations de la slide 3).

Légende des sources :
- **EC** : lu dans EC Perform (phases 1 à 5, sans écriture) ;
- **Calc** : calculé à la génération, jamais saisi ;
- **Circuit** : enregistré par le circuit de validation de la note ;
- **Saisie** : saisi dans l'écran de préparation de la note (nouveau bloc `saisie` du document `rapports`) ;
- **Fixe** : texte du modèle, conservé tel quel.

---

## 0. Identification des zones dans le template

Le modèle est copié dans `backend/templates/note_synthese.pptx`. Un script versionné
(`backend/scripts/preparer_modele_note.py`) renomme les formes, ce qui permet de refaire l'opération si le cabinet
publie une v2 du modèle. Il ne change rien d'autre que les noms. Le générateur ne repère les zones **que par nom de forme**
(et par ligne et colonne dans les tableaux), jamais par position ni par texte.

Règles de remplissage :
- On remplace le texte des **runs** sans toucher à `<a:rPr>` (police, taille, gras) ni à `<a:pPr>` (alignement,
  espacement). Seul `solidFill` passe de `D0021B` à la couleur normale de la zone.
- Pour une liste (un paragraphe par élément), on duplique le premier paragraphe, puis on supprime les paragraphes en trop.
- Donnée manquante : le run reste **rouge entre crochets** dans le brouillon, et un avertissement nommant la zone
  s'affiche à l'écran. L'approbation (et, je le propose, la soumission en revue : cf. Q5) est bloquée tant que le
  fichier contient un `[`.
- Les notes de l'orateur sont supprimées (`notesSlide` et relations).

Pied de page de toutes les slides (2 à 13) : `pied_texte` = « Y3 Audit & Conseils · Note de synthèse · {client} ·
Exercice clos le {date de clôture} · Document interne » (EC) ; `pied_page` = « {n} / {total} » (Calc, y compris les slides
de continuation).

---

## 1. Mapping par slide

### Slide 1 – Couverture

| Zone (nom proposé) | Contenu du modèle | Source | Détail |
|---|---|---|---|
| `couv_titre` (ZoneTexte 6) | [Client] / Comptes de l'exercice clos le [31/12/N] | EC | Client : `fiche.denomination`, sinon `client.raisonSociale` (même règle que l'ancien rapport). Date de clôture : `mission.exercice` + jour et mois de fin de `client.exerciceComptable` (« 31/12 - 31/12 ») ; à défaut « 31/12 ». |
| ZoneTexte 7 | Mission de tenue et de présentation… | Fixe | Je propose de le garder fixe (Q9). |
| `couv_circuit` (ZoneTexte 9), 3 paragraphes | Préparée par / Revue par / Approuvée par : [nom], le [date] | Circuit | Nom de l'employé et date de chaque étape. Tant qu'une étape n'est pas franchie : « — » en gris, pas de crochet rouge (cf. § 3). |
| `couv_ref` (ZoneTexte 11) | Réf. dossier : [code client] | Saisie | Il n'existe pas de code client dans EC Perform (Q8). |
| ZoneTexte 5, 10 ; logo | Mentions et logo | Fixe | |

### Slide 2 – Sommaire

| Zone | Source | Détail |
|---|---|---|
| `som_page_synthese`, `som_page_1` à `som_page_4` | Calc | Numéro de la première slide de chaque partie, recalculé après l'insertion des slides de continuation. |
| Autres textes | Fixe | |

### Slide 3 – Synthèse en une page

| Zone | Source | Détail |
|---|---|---|
| `statut_pret`, `statut_reserve`, `statut_non` (ellipses 9, 11, 13) | Saisie | Statut choisi parmi les trois. L'ellipse retenue est remplie (vert Y3 `80C342`) avec une coche ; les autres restent vides. |
| `statut_consigne` (ZoneTexte 15 « Cocher le statut retenu : [statut] ») | Saisie | Remplacé par « Statut retenu : {libellé} ». Avertissement non bloquant si « Comptes prêts à signer » est retenu alors que des cycles ne sont pas clôturés ou que le total des ajustements non passés dépasse le seuil. |
| `kpi_ca`, `kpi_rn`, `kpi_cp`, `kpi_treso` | EC | Chiffre d'affaires (XB), résultat net (XI), capitaux propres, trésorerie nette N, en M FCFA à 1 décimale (cf. § 2). |
| `kpi_ca_var`, `kpi_rn_var` | Calc | « +12,3 % vs N-1 ». Base N-1 nulle ou de signe opposé : « n.s. ». |
| `kpi_treso_var` | Calc | Variation **en valeur** (« +4,2 vs N-1 »), comme dans le modèle. |
| `kpi_cp_moitie` | Calc | « ≥ ½ du capital social » ou « < ½ du capital social » (cf. § 2.3). Dans le second cas, la mention est mise en rouge d'alerte et un point est proposé dans « Décisions attendues ». |
| `points_cles` (ZoneTexte 39, 3 paragraphes) | Saisie | De 1 à 3 points. |
| `decisions` (ZoneTexte 43) | Saisie, avec pré-remplissage Calc | Proposé à la première ouverture : une ligne par ajustement non passé (« {constat} : {montant} M FCFA, incidence sur le résultat »), et l'alerte sur les capitaux propres. Ensuite modifiable librement. |

### Slide 4 – Rappels de la mission et livrables (tableau `tab_livrables`)

| Colonne | Source | Détail |
|---|---|---|
| Domaine, Prestation prévue, Volume ou livrable, Statut | Saisie | Tableau éditable, pré-rempli avec les 6 lignes du modèle (texte noir du modèle et zones rouges vides). Statut : Fait / En cours / À faire / Hors mission. Nombre de lignes libre. |

### Slide 5 – Intervention et déroulement

| Zone | Source | Détail |
|---|---|---|
| `equipe` (ZoneTexte 12) – Associé signataire | Saisie | Associé désigné dans l'écran de préparation (liste des employés de grade Associé). C'est aussi lui qui pourra approuver (Q3). |
| – Chef de mission | EC | `intervenants(mission, "manager")` (noms de la mission, Phase 1/3). |
| – Collaborateur(s) | EC | `mission.equipe` + affectés aux cycles (`cycleAssignments`), hors chef de mission et associé : « Prénom Nom, grade ». Une ligne par personne. |
| `hors_perimetre` (ZoneTexte 16) | Saisie | Liste ; les 2 exemples du modèle sont proposés, cochables. |
| `calendrier` – Réception de la balance | EC | `dateReception` du document balance N (Phase 1, `balance_candidates`). |
| – Revue du chef de mission | EC | Date de la dernière validation de niveau Manager sur les cycles (`cycle_revisions.validations.manager.le`). |
| – Réunion de synthèse | Saisie | Date **prévue** (la note est préparée avant la réunion). Si la restitution client est déjà renseignée, sa date est proposée. |
| – Dépôt de la DSF / limite légale | Saisie | Deux dates. |
| Chevrons « Déroulement » | Fixe | |
| `ecart_calendrier` (ZoneTexte 27) | Saisie | Texte libre (« aucun » par défaut). |

### Slide 6 – Difficultés et améliorations (tableau `tab_difficultes`)

| Colonne | Source | Détail |
|---|---|---|
| Domaine, Difficulté, Amélioration proposée, En réunion (Oui/Non) | Saisie | Pré-rempli avec les 5 lignes du modèle comme suggestions modifiables ou supprimables. Nombre de lignes libre. |

### Slide 7 – Faits marquants et post-clôture

| Zone | Source | Détail |
|---|---|---|
| `faits_marquants` (ZoneTexte 12) | Saisie | Liste. Les exemples du modèle servent d'indications de saisie, pas de valeurs. |
| `perspectives` (ZoneTexte 16) | Saisie | Liste. Chaque événement post-clôture est qualifié « à ajuster » ou « à mentionner en notes annexes » (consigne de la slide). |

### Slide 8 – Chiffres clés N / N-1 (tableau `tab_chiffres`, 8 lignes fixes)

| Colonne | Source | Détail |
|---|---|---|
| Agrégat | Fixe | |
| N, N-1 | EC | Postes du compte de résultat et du bilan SYSCOHADA révisé calculés depuis les balances N et N-1 (§ 2). M FCFA, 1 décimale. |
| Variation, Var. % | Calc | Var. % « n.s. » si la base N-1 est nulle ou de signe opposé. |
| Explication | Saisie | Une par ligne. **Obligatoire** (zone rouge et avertissement) quand \|Var. %\| > 10 % ou au-delà du seuil de variation fixé par le chef de mission (Saisie, 10 % par défaut). |

### Slide 9 – Cascade du résultat net (graphique natif)

Les formes dessinées (rectangles 9 à 33, ZoneTexte 34 « Schéma indicatif ») sont supprimées et remplacées par un
graphique en **barres empilées** (`chart_cascade`), avec 3 séries :
- `Base`, invisible (sans remplissage), qui porte chaque barre flottante ;
- `Favorable` en vert `80C342` ;
- `Défavorable` en rouge `D0021B`.

Les barres extrêmes « Résultat N-1 » et « Résultat N » sont pleines, en navy `073E5D`. Les étiquettes de données sont en
position `ctr`. Les libellés de catégories en 8 pt suivent le gris du modèle (`4A5568`).

| Élément | Source | Détail |
|---|---|---|
| Résultat N-1, Résultat N | EC | XI N-1 et XI N (§ 2). |
| Causes (3 à 6) | Calc pré-rempli, puis Saisie | Proposition par défaut, dont la somme vaut exactement XI N − XI N-1 par construction : ① Marge sur activité = Δ(XB + TE…TI + RA…RF), ② Charges de personnel = ΔRK, ③ Autres charges externes = Δ(RG + RH + RI + RJ), ④ Dotations et provisions = Δ(TJ + RL), ⑤ Résultat financier et HAO = Δ(XF + XH), ⑥ Impôt sur le résultat = Δ(RQ + RS). L'utilisateur peut renommer, fusionner ou saisir ses propres causes et montants (Q6). |
| Contrôle | Calc | Σ causes = XI N − XI N-1, au FCFA près. Sinon, l'écran l'affiche, le brouillon est généré avec un avertissement, et **la soumission et l'approbation sont bloquées** avec un message indiquant l'écart. Le contrôle est fait sur les données et non sur le fichier. |

### Slide 10 – Points relevés (tableau `tab_points`, ligne Total en dernier)

Les lignes viennent des **constats de la Phase 4** (`cycle_revisions.constats`), complétés dans la note (indexés par id de
constat, sans modifier la Phase 4). La Phase 4 n'a ni incidence chiffrée, ni type, ni traitement (Q2).

| Colonne | Source | Détail |
|---|---|---|
| Retenu dans la note | Saisie | Case à cocher par constat ; par défaut, les constats de sévérité Moyen ou Élevé sont retenus. |
| N° | Calc | Numérotation continue des lignes retenues. |
| Cycle | EC | Libellé du cycle (`CYCLES`). |
| Constat | EC + Saisie | Texte du constat de la Phase 4 ; un titre court optionnel le remplace s'il est saisi (reprend `ConstatSaisie.titre`). |
| Incidence résultat (M FCFA) | Calc ou Saisie | Si le constat est rattaché à une **écriture** (regroupement équilibré d'ajustements de la Phase 4, mécanisme existant `saisie.ecritures` repris) : Σ(crédit − débit) des lignes sur les comptes des classes 6, 7 et 8. Sinon : montant saisi, ou « n.a. ». |
| Type | Saisie | Ajustement passé / Ajustement non passé / Point d'attention / Recommandation. La pastille de couleur reprend la légende du modèle (rectangles 9 à 12). |
| Traitement retenu | Saisie | Texte. |
| **Total des ajustements non passés** | Calc | Σ incidences des lignes « Ajustement non passé ». |
| Seuil de signification | Saisie | Montant fixé par le chef de mission (il n'existe dans aucune phase). Cellule : « Seuil de signification : {seuil} – {dépassé / non dépassé} ». |

### Slide 11 – Social, fiscal, N+1

| Zone | Source | Détail |
|---|---|---|
| `social`, `fiscal`, `suivi_n1` | Saisie | Trois listes. |
| `docs_cloture` – Dossier de travail complet par cycle | Calc | « oui » si les 13 cycles sont au statut `cloture` ; sinon « non, cycles manquants : B, C… ». |
| – Lettre d'affirmation | Saisie | Reçue le {date} / à obtenir. |
| – Lettre de recommandations | Saisie | À émettre / sans objet. « À émettre » est proposé quand une ligne de la slide 10 est de type Recommandation. |

### Slide 12 – Temps, honoraires, rentabilité

| Zone | Source | Détail |
|---|---|---|
| `tab_temps` : heures budgétées / passées par intervenant | Saisie | EC Perform n'a ni feuille de temps ni budget. Les 3 lignes du modèle sont fixes. |
| Écart, ligne Total | Calc | Passées − budgétées ; totaux. |
| `tab_honoraires` : prévus, facturés, encaissés | Saisie | M FCFA HT. |
| Reste à encaisser | Calc | Facturés − encaissés. |
| `rentabilite` – Taux de réalisation | Calc | Facturés / valeur des temps passés. Valeur des temps = Σ heures passées × taux horaire de la ligne. Le taux horaire est saisi par ligne (Q7). |
| – Causes du dépassement, travaux hors lettre de mission | Saisie | |

### Slide 13 – Maintien de la mission et validation

| Zone | Source | Détail |
|---|---|---|
| `maintien` : proposition, LBC-FT, indépendance, comportement du client | Saisie | Proposition : liste fermée (maintenir / maintenir sous conditions / ne pas maintenir). Les trois autres zones sont du texte. |
| `lettre_mission` : à reconduire / à réviser, date d'envoi | Saisie | Choix, détail de la révision, date. |
| `tab_validation` : Nom et Date des lignes Préparée / Revue / Approuvée | Circuit | Rempli automatiquement. La colonne Visa reste vide (visa manuscrit). |

---

## 2. Agrégats financiers (slides 3, 8 et 9)

Source : balances N et N-1 déposées en Phase 1 et lues par `balance_service.parse_balance_document` (déjà utilisé par
l'ancien rapport). Solde = débit − crédit de clôture, par compte. Aucun état financier structuré n'existe dans EC Perform
(le cycle M n'a pas de plage de comptes), donc les postes sont calculés **par la table de correspondance officielle des
comptes aux postes**. Les soldes sont ensuite enchaînés comme sur le compte de résultat, sans raccourci ni regroupement
approximatif.

### 2.1 Compte de résultat SYSCOHADA révisé (produits +, charges −)

| Réf. | Poste | Comptes |
|---|---|---|
| TA | Ventes de marchandises | 701 |
| RA | Achats de marchandises | 601 |
| RB | Variation de stocks de marchandises | 6031 |
| **XA** | **Marge commerciale** | TA + RA + RB |
| TB | Ventes de produits fabriqués | 702, 703, 704 |
| TC | Travaux, services vendus | 705, 706 |
| TD | Produits accessoires | 707 |
| **XB** | **Chiffre d'affaires** | TA + TB + TC + TD |
| TE | Production stockée (ou déstockage) | 73 |
| TF | Production immobilisée | 72 |
| TG | Subventions d'exploitation | 71 |
| TH | Autres produits | 75 |
| TI | Transferts de charges d'exploitation | 781 |
| RC | Achats de matières premières et fournitures liées | 602 |
| RD | Variation de stocks de matières premières | 6032 |
| RE | Autres achats | 604, 605, 608 |
| RF | Variation de stocks d'autres approvisionnements | 6033 |
| RG | Transports | 61 |
| RH | Services extérieurs | 62, 63 |
| RI | Impôts et taxes | 64 |
| RJ | Autres charges | 65 |
| **XC** | **Valeur ajoutée** | XB + RA + RB + TE à RJ |
| RK | Charges de personnel | 66 |
| **XD** | **Excédent brut d'exploitation** | XC + RK |
| TJ | Reprises d'amortissements, provisions et dépréciations | 791, 798, 799 |
| RL | Dotations aux amortissements, provisions et dépréciations | 681, 691 |
| **XE** | **Résultat d'exploitation** | XD + TJ + RL |
| TK, TL, TM | Revenus financiers ; reprises financières ; transferts de charges financières | 77 ; 797 ; 787 |
| RM, RN | Frais financiers ; dotations financières | 67 ; 697 |
| **XF** | **Résultat financier** | TK + TL + TM + RM + RN |
| **XG** | **Résultat des activités ordinaires** | XE + XF |
| TN, TO | Produits des cessions d'immobilisations ; autres produits HAO | 82 ; 84, 86, 88 |
| RO, RP | Valeurs comptables des cessions ; autres charges HAO | 81 ; 83, 85 |
| **XH** | **Résultat HAO** | TN + TO + RO + RP |
| RQ | Participation des travailleurs | 87 |
| RS | Impôts sur le résultat | 89 |
| **XI** | **Résultat net** | XG + XH + RQ + RS |

Contrôles (avertissements) :
- un compte des classes 6, 7 ou 8 non rattaché à un poste est signalé avec son numéro (aucun compte ignoré en silence) ;
- XI doit être égal au solde des classes 6 à 8 ;
- pour N-1, XI est comparé au compte 13 de la balance N (résultat N-1 en attente d'affectation), quand il est présent ;
- **une balance N-1 dont les classes 6 et 7 sont soldées** (balance après affectation) rend le N-1 inexploitable. Les
  colonnes N-1 sont alors laissées en zones signalées, avec un avertissement. *La mission fictive SAVEDO est dans ce cas :
  ses comptes de gestion N-1 seront ajoutés au script de démo.*

### 2.2 Bilan

| Agrégat | Calcul |
|---|---|
| Capitaux propres | Poste CP : comptes 10 (sauf 109, en déduction), 11, 12, 13, 14, 15, **+ XI de l'exercice**. Le résultat N n'est pas encore en 13 dans une balance avant affectation : on ajoute le résultat calculé, et on ne compte pas le compte 13 deux fois s'il est déjà mouvementé. |
| Dettes financières | Poste DD : comptes 16, 17 et 19. Ma proposition est d'exclure les provisions (19) (Q10). |
| Trésorerie nette | Trésorerie-actif (comptes 50, 51, 52 à 58 à solde débiteur) − trésorerie-passif (561, 564, 565, 566 et comptes 52 à solde créditeur). Le sens est déterminé compte par compte. |
| Capital social (½) | Poste CA : comptes 101 à 104, diminués de 109. Si la balance n'a pas de capital, on prend `fiche.capitalSocial` (Phase 1) ; si les deux existent et diffèrent, un avertissement est émis. Test : CP N ≥ CA / 2. |

### 2.3 Balance de base : avant ou après ajustements ?

La consigne de la slide 8 demande les montants des **états financiers définitifs**. Or la balance N déposée en Phase 1
est celle du client, avant les ajustements de la révision. Je propose : balance N **+ lignes des écritures typées
« Ajustement passé »** (slide 10), et l'écran l'indique. C'est la question Q1.

---

## 3. Circuit de validation

Statuts du document `rapports` : `brouillon` → `preparee` → `revue` → `approuvee`. Le statut `approuvee` remplace
`emis` : version figée, lecture seule.

| Action | Qui | Effet |
|---|---|---|
| Générer, régénérer, éditer, saisir | Collaborateur affecté (`est_affecte`) | Seulement au statut `brouillon`. La régénération garde son blocage actuel (session ONLYOFFICE ouverte ; modifications ONLYOFFICE à écraser seulement avec confirmation). |
| Soumettre (« Préparée ») | Collaborateur affecté | Contrôles bloquants : cascade équilibrée, aucun `[` dans la dernière version (Q5). Enregistre `{par, le}`. |
| Valider la revue (« Revue ») | Chef de mission : manager désigné sur la mission (Q4) | Enregistre `{par, le}`. |
| Approuver (« Approuvée ») | Associé signataire désigné (Q3) | Contrôles bloquants : cascade équilibrée, aucun `[`. Enregistre `{par, le}`, crée la version figée, lance l'export PDF (mécanisme existant). |
| Rejeter | L'acteur de l'étape suivante | **Commentaire obligatoire.** Revient à l'étape précédente : un rejet en revue repasse la note à `brouillon` ; un rejet à l'approbation la repasse à `preparee`, et efface le visa « Revue ». Rejets conservés dans un `historique`. |

Report des noms et dates dans le fichier : à chaque étape, le serveur **met à jour seulement** `couv_circuit` et
`tab_validation` dans la dernière version, à partir de leurs noms de forme, et enregistre une nouvelle version
(origine `circuit`). Il ne régénère pas : les modifications faites dans ONLYOFFICE sont conservées. Si une forme
nommée a disparu après une édition dans ONLYOFFICE, l'étape est refusée avec un message. Les zones du circuit non
encore franchies sont écrites « — » en gris, ce qui ne bloque pas le contrôle des crochets.

Une seule personne ne peut pas cumuler la préparation et la revue (Q4).

---

## 4. Code existant : supprimé, réutilisé, adapté

### Réutilisé tel quel
- `onlyoffice_service.py` : config JWT, callback, co-édition, `convertir_pdf`. Seul le test `statut == "emis"` devient
  « lecture seule », c'est-à-dire `approuvee`.
- `EditeurOnlyoffice.vue`.
- Dans `rapport_service.py` : GridFS (bucket `rapport_fichiers`), `ajouter_version`, sessions d'édition, blocage de la
  régénération, téléchargement, export PDF et relance.
- `restitution_service.py`, `RestitutionClient.vue`, modèles `Reunion` / `CommentaireConstat` : écran conservé. Son
  verrou `statut == "emis"` est à revoir (Q11).
- `balance_service` / `balance_engine` (lecture des balances) et `donnees._client`, `donnees._balances`.

### Adapté
- `rapport_service.py` : `droits()`, `emettre()` (remplacé par le circuit), sérialisation (circuit, contrôles,
  avertissements), `nom_fichier` (`Note_synthese_…`), `_contexte_saisie` (constats et ajustements uniquement).
- `models/rapport.py` : `SaisieRapport` remplacé par `SaisieNote` (§ 1). Sont réutilisés : `ConstatSaisie.titre` (étendu
  avec `retenu`, `type`, `incidence`, `traitement`, `ecritureIds`) et `Ecriture` avec la validation d'équilibre de
  `_normaliser` (incidence et ajustements passés).
- `services/rapport/donnees.py` : collecte réduite à ce que la note consomme, plus le calcul des postes (§ 2), dans un
  nouveau module pur `services/rapport/agregats.py` testable sans base.
- `services/rapport/pagination.py` : l'estimation de hauteur des lignes de tableau (`largeurs_colonnes`,
  `hauteur_ligne`) est reprise pour la réduction de police (jusqu'à 9 pt), puis pour la slide de continuation.
- `core/permissions.py` : `peut_emettre_rapport` / `RANG_EMISSION_RAPPORT` remplacés par les droits du circuit.
  `peut_ouvrir_mission` (accès des Associés à toutes les missions) est conservé à l'identique, la constante restant
  sous un autre nom.
- `useRapport.js`, `EmissionRapport.vue` → écran « Note de synthèse » (génération, avertissements, versions, éditeur,
  circuit avec rejet commenté).
- `PreparationRapport.vue` → réécrit en `PreparationNote.vue`, un onglet par partie (Synthèse, Mission, Économique,
  Technique, Administrative). Il reprend le squelette existant : autosave avec verrou optimiste et éditeur d'écritures.
- `scripts/demo_savedo.py` : saisie de la note, comptes de gestion N-1, constats typés, un ajustement non passé.
- `tests/test_rapport.py` → `tests/test_note_synthese.py` : les tests ONLYOFFICE, JWT, callback, PDF et restitution sont
  conservés et adaptés ; les tests de génération sont réécrits (cf. Vérification).
- `CLAUDE.md`, section Phase 6.

### Supprimé
- `backend/scripts/construire_modele.py`, `backend/templates/rapport_template.pptx`, `backend/templates/assets/` (fonds,
  logos, visuel de fin : utilisés seulement par ce script).
- `services/rapport/builders.py`, `assembleur.py`, `textes.py` : remplacés par `remplissage.py` (remplissage des formes
  nommées, tableaux, couleurs), `cascade.py` (graphique) et `note.py` (assemblage, continuation, pagination, sommaire).
- `services/rapport/formules.py` (il n'évaluait les papiers de travail que pour les blocs « papier »).
- Dans le modèle de données et dans l'écran : `points` par cycle et `blocs` (balance, variation, tableau, grand livre,
  papier, écriture), `GrandLivre`, `LigneGrandLivre`, `FiltreGrandLivre`, `Bloc`, `Point`, `LettreMission`,
  `contexteComplement`, `actionnariat`, `intangibiliteCommentaire`, `dateRapport`, `risques` et `retenirCI` des
  constats, `medias` (logo et photo du client) avec leurs 3 routes.
- `docs/phase6/mapping_rapport.md` : marqué « remplacé par mapping_note_synthese.md » (je propose de le garder pour
  l'historique). `rapport_exemple.pptx` est gitignoré et n'est pas touché.
- Phases 1 à 5 : **aucune modification**.

### Données existantes
Les documents `rapports` de la base de dev ont l'ancienne forme. Je propose de les supprimer, avec leurs fichiers GridFS,
par un script ponctuel (Q12).

---

## 5. Questions

**Q1. Montants « définitifs ».** Slides 3, 8 et 9 : balance N **+ ajustements passés** (ma proposition), ou balance N
telle que déposée ?

**Q2. Slide 10.** Je propose de partir des constats de la Phase 4, que l'on complète dans la note (retenu, type,
incidence, traitement), et de calculer l'incidence quand le constat est rattaché à une écriture d'ajustements. Faut-il
aussi pouvoir ajouter des points qui ne sont pas des constats de la Phase 4 ?

**Q3. Associé signataire.** La mission n'a pas de champ « associé ». Ma proposition : il est désigné dans la note (parmi
les employés de grade Associé), et seul lui peut approuver. Variante : n'importe quel Associé peut approuver.

**Q4. Chef de mission.** Le relecteur est-il l'un des managers désignés sur la mission (`managers`, simples noms), ou
tout affecté de rang Manager ou plus ? Interdit-on à la même personne de préparer et de revoir ?

**Q5. Crochets.** L'absence de `[` est-elle exigée dès la soumission en revue (ma proposition), ou seulement à
l'approbation ?

**Q6. Cascade.** Est-ce que je propose par défaut les 6 causes calculées du § 1 (slide 9), que l'utilisateur peut
fusionner ou renommer, ou est-ce que les causes sont entièrement saisies ?

**Q7. Taux horaires.** Il n'existe pas de grille de taux dans EC Perform. Faut-il les saisir dans chaque note (ma
proposition pour la V1), ou créer une grille du cabinet par grade ?

**Q8. Réf. dossier.** Le client n'a pas de « code client ». Faut-il le saisir dans la note, ou reprendre un champ
existant (n° de compte contribuable, RCCM) ?

**Q9. Libellé de la mission** (couverture) : fixe, ou à choisir (tenue ou présentation seule, avec ou sans social et
fiscal) ?

**Q10. Dettes financières.** Comptes 16 et 17 seulement, ou avec les provisions pour risques et charges (19), comme dans
le poste DD ?

**Q11. Ordre et libellé des sous-étapes de la Phase 6.** La note est préparée **avant** la réunion avec le client. Je
propose :
1. **« Note de synthèse »** (préparation, génération, circuit) ;
2. **« Restitution client »** (réunion, commentaires du client et réponses de la direction), qui garde son contenu
   actuel.

La restitution n'alimente plus aucun document généré : le compte rendu au client reste un document distinct. Faut-il
verrouiller la restitution tant que la note n'est pas approuvée, ou la laisser toujours ouverte ? Autre libellé possible
pour la sous-étape : « Note de synthèse (interne) ».

**Q12.** Puis-je supprimer les documents `rapports` et les fichiers de l'ancien rapport de la base de dev ?

---

## 6. Vérification prévue (après validation)

1. Génération sur SAVEDO SA : 13 slides, aucun `[` (saisie complète), montants attendus de la slide 8 calculés à la main
   depuis la balance de démo, cascade équilibrée, aucune note de l'orateur.
2. Tableau long (slide 10 avec 25 constats) : réduction de police jusqu'à 9 pt, puis slide de continuation « (suite) »
   avec en-tête répété, Total en dernière ligne de la dernière page, pagination « n / 14 » et sommaire mis à jour.
3. Cascade déséquilibrée : génération en brouillon avec avertissement, soumission et approbation refusées.
4. Rendu LibreOffice des 13 slides, comparé visuellement au rendu du modèle, slide par slide.
5. Circuit préparée → revue → rejet (commentaire) → brouillon → préparée → revue → approuvée. Pour chaque étape :
   couverture et slide 13 renseignées, droits refusés aux mauvais acteurs, lecture seule et PDF après l'approbation.
