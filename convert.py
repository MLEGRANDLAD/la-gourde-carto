import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

URL = "https://api-v3.tourinsoft.com/api/syndications/cdt44.tourinsoft.com/fe1d0351-e715-4163-8710-898a74aca525"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
}


def field(properties, name):
    element = properties.find(f"d:{name}", NS)
    return (element.text or "").strip() if element is not None else ""


def main():
    request = urllib.request.Request(URL, headers={"User-Agent": "LA-Gourde-Carto/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        root = ET.fromstring(response.read())

    entries = root.findall("atom:entry", NS)
    if not entries:
        raise RuntimeError("Aucune fiche dans le flux : fichier existant conservé.")

    features = []
    for entry in entries:
        properties = entry.find("atom:content/m:properties", NS)
        if properties is None:
            continue
        try:
            lat = float(field(properties, "Latitude").replace(",", "."))
            lon = float(field(properties, "Longitude").replace(",", "."))
        except ValueError:
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        name = field(properties, "NomOffre") or field(properties, "SyndicObjectName")
        if not name:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "name": name,
                "adresse": field(properties, "Adresse"),
                "commune": field(properties, "Commune"),
                "code_postal": field(properties, "CodePostal"),
                "id_tourinsoft": field(properties, "SyndicObjectID"),
            },
        })

    if not features:
        raise RuntimeError("Aucune fiche géolocalisée : fichier existant conservé.")
    result = {"type": "FeatureCollection", "features": features}
    Path("la_gourde.geojson").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(features)} établissements exportés")


if __name__ == "__main__":
    main()
