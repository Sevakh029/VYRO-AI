# Yerevan candidate network screening

**Screening date:** 2026-11-20  
**Tool version:** SUMO / NetEdit 1.28.0

All three generated networks in `simulation/osm/yerevan/` were opened in
NetEdit. This ranks their structural risk for follow-up, not traffic volume or
signal quality in operation. The OSM extracts contain no vehicle demand.

## Ranking

Ranked best to worst using an equal-weight screening score:

`(100 - largest connected-component coverage + unconnected external-lane rate) / 2`

The score combines SUMO `netcheck.py` connectivity using existing lane
connections with the share of external lanes that have no outgoing connection.
Lower is better. A lane endpoint may be a valid cul-de-sac or an extract-boundary
cut, so it is a risk indicator rather than a confirmed defect.

| Rank | Candidate | Score | NetEdit edges | External lanes | Lane ends without outgoing connection | `netcheck` components; largest coverage |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Barekamutyun / Kievyan | 18.8 | 518 | 541 | 80 (14.8%) | 75; 77.22% |
| 2 | Sasuntsi Davit / Tigran Mets | 37.1 | 745 | 909 | 210 (23.1%) | 199; 48.86% |
| 3 | Kentron / Republic Square | 46.8 | 2,225 | 2,617 | 1,120 (42.8%) | 1,100; 49.30% |

## Signals, lanes, and connections

| Candidate | Signal controllers | Orphan/missing signal logic | Phase-length errors | Invalid connection edge/lane references |
| --- | ---: | ---: | ---: | ---: |
| Barekamutyun / Kievyan | 9 | 0 | 0 | 0 |
| Sasuntsi Davit / Tigran Mets | 28 | 0 | 0 | 0 |
| Kentron / Republic Square | 84 | 0 | 0 | 0 |

Every signal controller has controlled connections, and each phase state
matches its controller's link count. The SUMO right-of-way check reported no
issues for these networks.

All three nets trigger `netcheck.py`'s disconnected-network warning when it
uses the encoded connections. With connections ignored, the largest-component
coverages are 90.15% for Barekamutyun, 98.39% for Sasuntsi Davit, and 99.87%
for Kentron. This points to movement connectivity as the primary follow-up
area, but is not by itself proof that each split is erroneous: ignoring
connections also treats prohibited turns as connected.

## Recommendation

Use **Barekamutyun / Kievyan** as the first candidate for demand and control
prototyping; it has the strongest connection-based coverage and lowest
unconnected-lane rate. Inspect the disconnected components and boundary
terminals in NetEdit before calibration. Sasuntsi Davit ranks ahead of Kentron
on the combined screening score because it has fewer unconnected lane ends;
both still have substantial connection-component fragmentation.

These are screening results only. Review OSM boundary cuts, turn restrictions,
and transit stops before treating any candidate as an experiment-ready network.
