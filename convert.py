
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

URL = (
    "https://wcf.tourinsoft.com/Syndication/3.0/cdt44/"
    "fe1d0351-e715-4163-8710-898a74aca525/"
    "Objects?$expand=MoyenCommunications"
)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
}


def field(properties, name):
    element = properties.find(f"d:{name}", NS)
    return (element.text or "").strip() if element is not None else ""


def contacts(entry):
    telephones = {}
    site = ""

    for link in entry.findall("atom:link", NS):
        if link.get("title") != "MoyenCommunications":
            continue

        for contact in link.findall("m:inline/atom:feed/atom:entry", NS):
            props = contact.find("atom:content/m:properties", NS)
            if props is None:
                continue

            valeur = field(props, "Coordonnees")
            code_element = props.find(
                "d:Moyendecommunication/d:ThesCode", NS
            )
            code = (
                (code_element.text or "").strip()
                if code_element is not None else ""
            )

            if code in ("C1", "C6") and valeur:
                telephones.setdefault(code, valeur)

            if code == "C5" and valeur and not site:
                if not valeur.startswith(("http://", "https://")):
                    valeur = "https://" + valeur

                parsed = urlsplit(valeur)
                if parsed.scheme in ("http", "https") and parsed.netloc:
                    site = valeur

    return telephones.get("C1") or telephones.get("C6", ""), site


def main():
    request = urllib.request.Request(
        URL, headers={"User-Agent": "LA-Gourde-Carto/1.0"}
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        root = ET.fromstring(response.read())

    entries = root.findall("atom:entry", NS)
    if not entries:
        raise RuntimeError("Flux vide : GeoJSON conservé.")

    features = []

    for entry in entries:
        props = entry.find("atom:content/m:properties", NS)
        if props is None:
            continue

        try:
            lat = float(field(props, "Latitude").replace(",", "."))
            lon = float(field(props, "Longitude").replace(",", "."))
        except ValueError:
            continue

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        name = field(props, "NomOffre") or field(
            props, "SyndicObjectName"
        )
        object_id = field(props, "SyndicObjectID")

        if not name or not object_id:
            continue

        telephone, site = contacts(entry)

        fiche = {
            "name": name,
            "adresse": field(props, "Adresse"),
            "commune": field(props, "Commune"),
            "code_postal": field(props, "CodePostal"),
            "id_tourinsoft": object_id,
            "latitude": lat,
            "longitude": lon,
        }

        if telephone:
            fiche["telephone"] = telephone

        if site:
            fiche["site_internet"] = site

        # Préparer le lien pour uMap.
        # Aucun lien si le site internet est absent.
        fiche["lien_site"] = (
            f"🌐 [[{site}|Site internet]]" if site else ""
        )

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
            "Aucun établissement géolocalisé : GeoJSON conservé."
        )

    result = {"type": "FeatureCollection", "features": features}

    Path("la_gourde.geojson").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"{len(features)} établissements exportés")


if __name__ == "__main__":
    main()
