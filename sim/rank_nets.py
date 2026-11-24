"""Screen candidate SUMO networks by size and structural indicators."""

import argparse
from dataclasses import dataclass
from pathlib import Path

import sumolib


@dataclass(frozen=True)
class NetworkSummary:
    name: str
    edge_count: int
    lane_count: int
    connection_count: int
    lanes_without_outgoing: int
    signal_count: int
    width_m: float
    height_m: float

    @property
    def meets_screening_limits(self) -> bool:
        return (
            self.signal_count <= 12
            and self.width_m <= 2000
            and self.height_m <= 2000
        )


def summarize_network(network_file: Path) -> NetworkSummary:
    network = sumolib.net.readNet(str(network_file), withPrograms=True)
    edges = network.getEdges()
    lanes = [lane for edge in edges for lane in edge.getLanes()]
    outgoing_counts = [len(lane.getOutgoing()) for lane in lanes]
    west, south, east, north = network.getBoundary()
    return NetworkSummary(
        name=network_file.stem,
        edge_count=len(edges),
        lane_count=len(lanes),
        connection_count=sum(outgoing_counts),
        lanes_without_outgoing=sum(count == 0 for count in outgoing_counts),
        signal_count=len(network.getTrafficLights()),
        width_m=east - west,
        height_m=north - south,
    )


def render_report(summaries: list[NetworkSummary]) -> str:
    ordered = sorted(
        summaries,
        key=lambda summary: (
            not summary.meets_screening_limits,
            summary.lanes_without_outgoing,
            summary.signal_count,
            summary.name,
        ),
    )
    lines = [
        "# Yerevan candidate network screening",
        "",
        "Generated from the checked-in `.net.xml` candidates with SUMO sumolib.",
        "This is structural screening, not a traffic-volume or calibration result.",
        "A lane with no outgoing connection may be a valid terminal or extract cut.",
        "",
        "| Rank | Candidate | Edges | Lanes | Lane connections | Lanes without outgoing | "
        "Signals | Projected extent (m) | Meets 12-signal / 2-km limits |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for rank, summary in enumerate(ordered, start=1):
        qualifies = "yes" if summary.meets_screening_limits else "no"
        lines.append(
            f"| {rank} | {summary.name} | {summary.edge_count} | "
            f"{summary.lane_count} | {summary.connection_count} | "
            f"{summary.lanes_without_outgoing} | {summary.signal_count} | "
            f"{summary.width_m:.2f} x {summary.height_m:.2f} | {qualifies} |"
        )
    lines.extend(
        [
            "",
            "The 2-km screen means both projected bounding-box dimensions are at "
            "most 2,000 m.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--nets",
        type=Path,
        default=Path(__file__).parent / "osm" / "yerevan",
        help="directory containing candidate .net.xml files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "area_report.md",
        help="report path",
    )
    args = parser.parse_args()
    summaries = [
        summarize_network(network_file)
        for network_file in sorted(args.nets.glob("*.net.xml"))
    ]
    if not summaries:
        raise FileNotFoundError(f"No .net.xml candidates found in {args.nets}")
    report = render_report(summaries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
