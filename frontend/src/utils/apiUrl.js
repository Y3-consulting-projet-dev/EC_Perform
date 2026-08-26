// En l'absence de VITE_API_URL, on déduit l'hôte de l'API à partir de celui utilisé pour
// charger la page (et non un "localhost" figé) : ça permet à un collègue sur le même réseau
// Wi-Fi d'ouvrir http://<ip-du-poste>:5173 et d'atteindre l'API sur ce même poste, port 8000.
export const API_URL = "http://192.168.0.109:5173/"
