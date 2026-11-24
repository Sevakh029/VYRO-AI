"""Export SUMO geometry to a Leaflet-compatible GeoJSON file."""

import argparse
import json
from pathlib import Path
from typing import Any


def export_geojson(network_file: Path, output_file: Path) -> dict[str, Any]:
    try:
        import sumolib
    except ImportError as exc:
        raise RuntimeError("sumolib is required for real network export") from exc

    network = sumolib.net.readNet(str(network_file), withPrograms=False)
    features = []
    for edge in network.getEdges():
        if len(edge.getShape()) < 2:
            continue
        coordinates = [
            list(network.convertXY2LonLat(x, y))
            for x, y in edge.getShape()
        ]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coordinates},
                "properties": {"edge_id": edge.getID()},
            }
        )
    collection = {"type": "FeatureCollection", "features": features}
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(collection, indent=2), encoding="utf-8")
    return collection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("network", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export_geojson(args.network, args.output)
