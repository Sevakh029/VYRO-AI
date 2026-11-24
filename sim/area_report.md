# Yerevan candidate network screening

Generated from the checked-in `.net.xml` candidates with SUMO sumolib.
This is structural screening, not a traffic-volume or calibration result.
A lane with no outgoing connection may be a valid terminal or extract cut.

| Rank | Candidate | Edges | Lanes | Lane connections | Lanes without outgoing | Signals | Projected extent (m) | Meets 12-signal / 2-km limits |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | barekamutyun_kievyan.net | 518 | 541 | 1011 | 80 | 9 | 1671.28 x 1942.80 | yes |
| 2 | sasuntsi_davit_tigran_mets.net | 745 | 909 | 1264 | 210 | 28 | 1336.11 x 3495.90 | no |
| 3 | kentron_republic_square.net | 2225 | 2617 | 2632 | 1120 | 84 | 2207.00 x 3389.05 | no |

The 2-km screen means both projected bounding-box dimensions are at most 2,000 m.
