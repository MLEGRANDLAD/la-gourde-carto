
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

URL = "https://api-v3.tourinsoft.com/api/syndications/cdt44.tourinsoft.com/fe1d0351-e715-4163-8710-898a74aca525"
CONTACTS_URL = "https://wcf.tourinsoft.com/Syndication/3.0/cdt44/fe1d0351-e715-4163-8710-898a74aca525"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
}


def field(properties, name):
    element = properties.find(f"d:{name}", NS)
    return (element.text or "").strip() if element is not None else ""


def fetch_xml(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "LA-Gourde-Carto/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return ET.fromstring(response.read())


def get_contacts(object_id):
    safe_id = urllib.parse.quote(object_id, safe="")
    url = f"{CONTACTS_URL}/Objects('{safe_id}')/MoyenCommunications"

    root = fetch_xml(url)
    telephone = ""
    site_internet = ""

    for entry in root.findall("atom:entry", NS):
        props = entry.find("atom:content/m:properties", NS)
        if props is None:
            continue

        valeur = field(props, "Coordonnees")
        code_element = props.find(
            "d:Moyendecommunication/d:ThesCode", NS
        )
        code = (
            (code_element.text or "").strip()
            if code_element is not None
            else ""
        )

        if code == "C1" and valeur and not telephone:
            telephone = valeur
        elif code == "C5" and valeur and not site_internet:
            if valeur.startswith(("https://", "http://")):
                site_internet = valeur
            else:
                site_internet = "https://" + valeur

    return telephone, site_internet


def main():
    root = fetch_xml(URL)
    entries = root.findall("atom:entry", NS)

    if not entries:
        raise RuntimeError(
            "Aucune fiche dans le flux : fichier existant conservé."
        )

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

        name = (
            field(properties, "NomOffre")
            or field(properties, "SyndicObjectName")
        )
        object_id = field(properties, "SyndicObjectID")

        if not name or not object_id:
            continue

        telephone, site_internet = get_contacts(object_id)

        fiche = {
            "name": name,
            "adresse": field(properties, "Adresse"),
            "commune": field(properties, "Commune"),
            "code_postal": field(properties, "CodePostal"),
            "id_tourinsoft": object_id,
        }

        if telephone:
            fiche["telephone"] = telephone

        if site_internet:
            fiche["site_internet"] = site_internet

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "properties": fiche,
        })

    if not features:
        raise RuntimeError(
            "Aucune fiche géolocalisée : fichier existant conservé."
        )

    result = {
        "type": "FeatureCollection",
        "features": features,
    }

    Path("la_gourde.geojson").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"{len(features)} établissements exportés")


if __name__ == "__main__":
    main()
