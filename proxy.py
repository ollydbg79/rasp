from flask import Flask, jsonify, abort
import json
import requests
import time
from urllib.parse import urlparse, parse_qs
from script import resolve_streamwish

app = Flask(__name__)

# URLs de los JSON en GitHub
PELICULAS_JSON_URL = "https://raw.githubusercontent.com/ollydbg79/basement/main/peliculas.json"
SERIES_JSON_URL = "https://raw.githubusercontent.com/ollydbg79/basement/main/series.json"

# Cargar JSON desde GitHub
def load_json(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Cargado {url}: {json.dumps(data, indent=2)[:500]}...")
        return data
    except Exception as e:
        print(f"Error al cargar {url}: {e}")
        return []

# Verificar si un enlace HLS está vigente
def is_hls_valid(hls_url):
    if not hls_url:
        return False
    try:
        parsed = urlparse(hls_url)
        params = parse_qs(parsed.query)
        expire = int(params.get('e', [0])[0])
        start = int(params.get('s', [0])[0])
        return start + expire > int(time.time())
    except:
        return False

# Normalizar título
def normalize_title(title):
    return title.lower().replace('_', ' ')

# Obtener enlace HLS para una película
@app.route('/pelicula/<title>/<opcion>')
def get_pelicula(title, opcion):
    peliculas = load_json(PELICULAS_JSON_URL)
    title = normalize_title(title)
    opcion_key = "Opcion 1" if opcion == "opcion1" else "Opcion 2"

    if not peliculas:
        abort(500, description="No se pudo cargar peliculas.json")

    if isinstance(peliculas, list):
        for peli in peliculas:
            if isinstance(peli, dict) and peli.get("Titulo", "").lower() == title:
                embed_url = peli.get(opcion_key)
                if not embed_url:
                    abort(404, description=f"{opcion_key} no encontrada para {title}")
                print(f"Procesando embed URL: {embed_url}")
                hls_url = resolve_streamwish(embed_url)
                if not hls_url:
                    abort(500, description=f"No se pudo generar HLS para {embed_url}")
                return jsonify({"hls": hls_url})
    else:
        abort(400, description="Formato inválido de peliculas.json")

    abort(404, description="Película no encontrada")

# Obtener enlace HLS para una serie
@app.route('/serie/<series_name>/t<season>/e<episode>/<opcion>')
def get_series_episode(series_name, season, episode, opcion):
    series = load_json(SERIES_JSON_URL)
    series_name = normalize_title(series_name)
    opcion_key = "Opcion 1" if opcion == "opcion1" else "Opcion 2"

    if not series:
        abort(500, description="No se pudo cargar series.json")

    if isinstance(series, list):
        for serie in series:
            if isinstance(serie, dict) and serie.get("Titulo", "").lower() == series_name:
                for temporada in serie.get("Temporadas", []):
                    # Soporta "Temporada" o "Numero" para compatibilidad
                    temp_num = temporada.get("Temporada") or temporada.get("Numero")
                    if temp_num == int(season):
                        for ep in temporada.get("Episodios", []):
                            if ep.get("Numero") == int(episode):
                                embed_url = ep.get(opcion_key)
                                if not embed_url:
                                    abort(404, description=f"{opcion_key} no encontrada para {series_name} T{season} E{episode}")
                                print(f"Procesando embed URL: {embed_url}")
                                hls_url = resolve_streamwish(embed_url)
                                if not hls_url:
                                    abort(500, description=f"No se pudo generar HLS para {embed_url}")
                                return jsonify({"hls": hls_url})
    elif isinstance(series, dict) and series.get("Titulo", "").lower() == series_name:
        for temporada in series.get("Temporadas", []):
            temp_num = temporada.get("Temporada") or temporada.get("Numero")
            if temp_num == int(season):
                for ep in temporada.get("Episodios", []):
                    if ep.get("Numero") == int(episode):
                        embed_url = ep.get(opcion_key)
                        if not embed_url:
                            abort(404, description=f"{opcion_key} no encontrada para {series_name} T{season} E{episode}")
                        print(f"Procesando embed URL: {embed_url}")
                        hls_url = resolve_streamwish(embed_url)
                        if not hls_url:
                            abort(500, description=f"No se pudo generar HLS para {embed_url}")
                        return jsonify({"hls": hls_url})

    abort(404, description="Episodio no encontrado")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
