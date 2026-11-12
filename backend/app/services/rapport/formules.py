"""Évaluation des formules des papiers de travail intégrés (Jspreadsheet), pour reprendre leurs
VALEURS dans le rapport. Pas de dépendance FastAPI / Mongo.

Convention Jspreadsheet : la ligne 1 est la première ligne de données (les titres de colonnes ne
sont pas des lignes), la colonne A est la première colonne.

Sous-ensemble supporté : nombres, textes "…", références A1 / $A$1, plages A1:B5, + - * / ^ &,
comparaisons (= <> < > <= >=), fonctions SUM/SOMME, AVERAGE/MOYENNE, MIN, MAX, COUNT/NB, ABS,
ROUND/ARRONDI, IF/SI, AND/ET, OR/OU. Toute autre formule lève FormuleNonSupportee : le rapport
signale la cellule au lieu d'inventer une valeur.
"""

import re

MAX_PROFONDEUR = 64


class FormuleNonSupportee(Exception):
    pass


_TOKEN = re.compile(
    r"\s*(?:(?P<num>\d+(?:[.,]\d+)?)|(?P<str>\"(?:[^\"]|\"\")*\")|"
    r"(?P<ref>\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)(?![A-Za-z(])|"
    r"(?P<fn>[A-Za-zÀ-ÿ_.]+)\s*\(|(?P<op><=|>=|<>|[-+*/^&=<>(),;]))"
)


def _col_index(lettres):
    n = 0
    for ch in lettres.upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _ref(texte):
    m = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?(\d+)", texte)
    return int(m.group(2)) - 1, _col_index(m.group(1))


def nombre(valeur):
    """Convertit une valeur de cellule en nombre, ou None si ce n'est pas un nombre."""
    if valeur is None or isinstance(valeur, bool):
        return None
    if isinstance(valeur, (int, float)):
        return float(valeur)
    texte = str(valeur).strip().replace(" ", "").replace(" ", "").replace(" ", "")
    if re.fullmatch(r"-?\d+([.,]\d+)?", texte):
        return float(texte.replace(",", "."))
    return None


def _tokens(formule):
    pos, out = 0, []
    while pos < len(formule):
        if formule[pos:].strip() == "":
            break
        m = _TOKEN.match(formule, pos)
        if not m:
            raise FormuleNonSupportee(formule)
        pos = m.end()
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
    return out


class Classeur:
    """Valeurs d'une feuille : data[ligne][colonne], les formules étant évaluées à la demande."""

    def __init__(self, data):
        self.data = data or []
        self.cache = {}
        self.en_cours = set()

    def valeur(self, r, c, profondeur=0):
        if (r, c) in self.cache:
            return self.cache[(r, c)]
        if r < 0 or r >= len(self.data) or c < 0 or c >= len(self.data[r]):
            return None
        brut = self.data[r][c]
        if isinstance(brut, str) and brut.startswith("="):
            if (r, c) in self.en_cours or profondeur > MAX_PROFONDEUR:
                raise FormuleNonSupportee("référence circulaire")
            self.en_cours.add((r, c))
            try:
                v = _Parser(self, _tokens(brut[1:]), profondeur + 1).evaluer()
            finally:
                self.en_cours.discard((r, c))
        else:
            v = brut
        self.cache[(r, c)] = v
        return v

    def plage(self, texte, profondeur):
        debut, _, fin = texte.partition(":")
        (r1, c1), (r2, c2) = _ref(debut), _ref(fin or debut)
        return [
            self.valeur(r, c, profondeur)
            for r in range(min(r1, r2), max(r1, r2) + 1)
            for c in range(min(c1, c2), max(c1, c2) + 1)
        ]


def _num(v):
    if v is None or v == "":
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    n = nombre(v)
    if n is None:
        raise FormuleNonSupportee(f"valeur non numérique : {v!r}")
    return n


def _vrai(v):
    return v if isinstance(v, bool) else _num(v) != 0


def _aplatir(args):
    return [v for a in args for v in (a if isinstance(a, list) else [a])]


def _nums(args):
    out = []
    for a in args:
        for v in a if isinstance(a, list) else [a]:
            n = nombre(v) if not isinstance(v, bool) else None
            if n is not None:
                out.append(n)
    return out


_FONCTIONS = {
    "SUM": lambda a: sum(_nums(a)), "SOMME": lambda a: sum(_nums(a)),
    "MIN": lambda a: min(_nums(a), default=0.0), "MAX": lambda a: max(_nums(a), default=0.0),
    "COUNT": lambda a: float(len(_nums(a))), "NB": lambda a: float(len(_nums(a))),
    "AVERAGE": lambda a: (sum(_nums(a)) / len(_nums(a))) if _nums(a) else 0.0,
    "ABS": lambda a: abs(_num(a[0])),
    "AND": lambda a: all(_vrai(x) for x in _aplatir(a)), "OR": lambda a: any(_vrai(x) for x in _aplatir(a)),
}
_FONCTIONS["MOYENNE"] = _FONCTIONS["AVERAGE"]
_FONCTIONS["ET"] = _FONCTIONS["AND"]
_FONCTIONS["OU"] = _FONCTIONS["OR"]


def _arrondi(a):
    chiffres = int(_num(a[1])) if len(a) > 1 else 0
    return float(round(_num(a[0]), chiffres))


class _Parser:
    def __init__(self, classeur, tokens, profondeur):
        self.cl, self.t, self.i, self.p = classeur, tokens, 0, profondeur

    def _peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def _next(self):
        tok = self._peek()
        self.i += 1
        return tok

    def _expect(self, op):
        kind, val = self._next()
        if kind != "op" or val != op:
            raise FormuleNonSupportee(f"attendu {op}")

    def evaluer(self):
        v = self._comparaison()
        if self.i != len(self.t):
            raise FormuleNonSupportee("syntaxe")
        return v

    def _comparaison(self):
        g = self._concat()
        kind, op = self._peek()
        if kind == "op" and op in ("=", "<>", "<", ">", "<=", ">="):
            self._next()
            d = self._concat()
            gn, dn = nombre(g), nombre(d)
            a, b = (gn, dn) if gn is not None and dn is not None else (str(g or ""), str(d or ""))
            return {"=": a == b, "<>": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
        return g

    def _concat(self):
        v = self._somme()
        while self._peek() == ("op", "&"):
            self._next()
            v = f"{'' if v is None else v}{'' if (d := self._somme()) is None else d}"
        return v

    def _somme(self):
        v = self._produit()
        while self._peek()[0] == "op" and self._peek()[1] in "+-":
            op = self._next()[1]
            d = self._produit()
            v = _num(v) + _num(d) if op == "+" else _num(v) - _num(d)
        return v

    def _produit(self):
        v = self._puissance()
        while self._peek()[0] == "op" and self._peek()[1] in "*/":
            op = self._next()[1]
            d = _num(self._puissance())
            if op == "*":
                v = _num(v) * d
            else:
                if d == 0:
                    raise FormuleNonSupportee("division par zéro")
                v = _num(v) / d
        return v

    def _puissance(self):
        v = self._unaire()
        if self._peek() == ("op", "^"):
            self._next()
            v = _num(v) ** _num(self._unaire())
        return v

    def _unaire(self):
        if self._peek() == ("op", "-"):
            self._next()
            return -_num(self._unaire())
        if self._peek() == ("op", "+"):
            self._next()
            return _num(self._unaire())
        return self._atome()

    def _atome(self):
        kind, val = self._next()
        if kind == "num":
            return float(val.replace(",", "."))
        if kind == "str":
            return val[1:-1].replace('""', '"')
        if kind == "ref":
            if ":" in val:
                raise FormuleNonSupportee("plage hors fonction")
            r, c = _ref(val)
            return self.cl.valeur(r, c, self.p)
        if kind == "op" and val == "(":
            v = self._comparaison()
            self._expect(")")
            return v
        if kind == "fn":
            return self._fonction(val.upper())
        raise FormuleNonSupportee(f"jeton inattendu {val!r}")

    def _arguments(self):
        args = []
        if self._peek() == ("op", ")"):
            self._next()
            return args
        while True:
            kind, val = self._peek()
            if kind == "ref" and ":" in val:
                self._next()
                args.append(self.cl.plage(val, self.p))
            else:
                args.append(self._comparaison())
            kind, val = self._next()
            if kind == "op" and val in (",", ";"):
                continue
            if kind == "op" and val == ")":
                return args
            raise FormuleNonSupportee("arguments")

    def _fonction(self, nom):
        args = self._arguments()
        if nom in ("IF", "SI"):
            if len(args) < 2:
                raise FormuleNonSupportee("SI")
            return args[1] if _vrai(args[0]) else (args[2] if len(args) > 2 else False)
        if nom in ("ROUND", "ARRONDI"):
            return _arrondi(args)
        if nom in _FONCTIONS:
            return _FONCTIONS[nom](args)
        raise FormuleNonSupportee(f"fonction {nom}")


def valeurs_feuille(data):
    """Renvoie (lignes de valeurs, nombre de cellules non évaluables). Une cellule dont la
    formule n'est pas supportée vaut "#FORMULE" : le rapport ne devine jamais de valeur."""
    classeur = Classeur(data)
    lignes, erreurs = [], 0
    for r, ligne in enumerate(classeur.data):
        sortie = []
        for c, _ in enumerate(ligne):
            try:
                sortie.append(classeur.valeur(r, c))
            except FormuleNonSupportee:
                erreurs += 1
                sortie.append("#FORMULE")
        lignes.append(sortie)
    return lignes, erreurs
