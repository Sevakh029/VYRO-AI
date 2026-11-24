import json
from pathlib import Path

from sim.export_geojson import export_geojson

NETWORK = (
    Path(__file__).parents[1]
    / "net"
    / "yerevan_v0.net.xml"
)


def test_export_geojson_uses_network_projection(tmp_path) -> None:
    output = tmp_path / "network.geojson"

    collection = export_geojson(NETWORK, output)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert collection == saved
    assert collection["features"]
    road = next(
        feature
        for feature in collection["features"]
        if feature["geometry"]["type"] == "LineString"
    )
    longitude, latitude = road["geometry"]["coordinates"][0]
    assert 44.48 <= longitude <= 44.51
    assert 40.19 <= latitude <= 40.22

    signals = [
        feature
        for feature in collection["features"]
        if feature["properties"].get("kind") == "signal"
    ]
    assert len(signals) == 9
    assert all(feature["geometry"]["type"] == "Point" for feature in signals)
    assert all(
        44.48 <= feature["geometry"]["coordinates"][0] <= 44.51
        and 40.19 <= feature["geometry"]["coordinates"][1] <= 40.22
        for feature in signals
    )
