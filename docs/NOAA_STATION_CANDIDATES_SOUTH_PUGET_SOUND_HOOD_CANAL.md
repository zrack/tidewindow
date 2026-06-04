# NOAA Station Candidates - South Puget Sound and South Hood Canal

_Created: 2026-06-04._

This is a planning reference for expanding TideWindow regions. I pulled these from NOAA CO-OPS station metadata and current-prediction listings, then scoped the list to stations that are useful for South Puget Sound, the Tacoma Narrows/Gig Harbor basin, central Kitsap/Bremerton/Port Orchard/Silverdale, and south/central Hood Canal.

## How To Read This

- Tide station type: `R` is a reference station and `S` is a subordinate tide-prediction station.
- Current station type: `H` is harmonic current prediction, `S` is subordinate current prediction, and `W` is weak/variable. For TideWindow scoring, prefer `H` where possible.
- `Reference` on tide rows is the NOAA reference station used by a subordinate station. Many Puget Sound subordinate tide predictions reference Seattle (`9447130`), even when a better nearby current station is available.
- Current rows may include multiple bins/depths. For a surface planning aid, the shallowest practical bin is usually the first candidate, but the app should label which bin/depth it uses.

## Recommended First Additions

1. South Sound region set: Tacoma Narrows, Gig Harbor, Carr Inlet, Case Inlet, Nisqually Reach, Anderson Island, Steilacoom.
   - Tide anchors: `9446484` Tacoma, `9446291` Wauna, `9446804` Sandy Point Anderson Island, `9446807` Budd Inlet.
   - Current anchors: `PUG1527` The Narrows, `PUG1528` Narrows South, `PUG1530` Hale Passage West, `PUG1532` Steilacoom, `PUG1534` Nisqually Reach, `PUG1538` Devils Head.
2. Olympia and inlets region set: Budd, Eld, Totten, Pickering, Hammersley, Oakland Bay.
   - Tide anchors: `9446807` Budd Inlet/Olympia Shoal, `9446969` Olympia, `9446628` Shelton, `9446666` Arcadia, `9446742` Barron Point.
   - Current anchors: `PUG1540` Budd Inlet Entrance, `PUG1544` Totten Inlet Entrance, `PUG1545` Libby Point/Hammersley, `PCT1896` Hammersley west of Skookum Point.
3. South Hood Canal region set: Union, Lynch Cove, Ayock Point, Triton Head, Seabeck.
   - Tide anchors: `9445478` Union, `9445441` Lynch Cove Dock, `9445388` Ayock Point, `9445326` Triton Head.
   - Current anchors: `PUG1601` Hazel Point, `PUG1602` South Point, `PCT1596` Chinom Point. Hood Canal current coverage is thinner, so confidence labeling matters.
4. Central Kitsap refinement: Bremerton, Port Orchard, Silverdale, Dyes Inlet, Rich Passage.
   - Tide anchors: `9445958` Bremerton, plus `9445901` Tracyton and `9445832` Brownsville as local tide-prediction candidates.
   - Current anchors: `PUG1510` Port Washington Narrows, `PUG1513` Rich Passage East, `PUG1514` Rich Passage West, `PUG1508` Liberty Bay entrance.

## Active Water-Level Stations

These are real-time NOAA water-level stations in or near the app's target expansion area.

| Station | Name | Lat | Lon | App note |
| --- | --- | ---: | ---: | --- |
| `9445958` | Bremerton | 47.5617 | -122.6230 | Best station-backed tide anchor for Bremerton/Port Orchard/Silverdale. |
| `9446484` | Tacoma | 47.2667 | -122.4133 | Best station-backed tide anchor for Tacoma Narrows/Gig Harbor/South Sound. |

## Tide-Prediction Stations

### Central Kitsap, Bremerton, Port Orchard, Silverdale

| Station | Name | Type | Lat | Lon | Reference | App note |
| --- | --- | --- | ---: | ---: | --- | --- |
| `9445719` | Poulsbo, Liberty Bay | S | 47.7250 | -122.6380 | `9447130` | Useful north boundary for Liberty Bay/Silverdale expansion. |
| `9445832` | Brownsville, Port Orchard | S | 47.6517 | -122.6150 | `9447130` | Good east-side Dyes Inlet/Brownsville tide candidate. |
| `9445901` | Tracyton, Dyes Inlet | S | 47.6100 | -122.6600 | `9447130` | Useful for Silverdale and Dyes Inlet spots. |
| `9445938` | Clam Bay, Rich Passage | S | 47.5733 | -122.5430 | `9447130` | Useful for Rich Passage/Manchester. |
| `9445958` | Bremerton, Sinclair Inlet, Port Orchard | R | 47.5617 | -122.6230 |  | Primary station-backed tide anchor for central Kitsap. |
| `9445993` | Harper, Yukon Harbor | S | 47.5233 | -122.5170 | `9447130` | Useful for Manchester/Southworth/Colvos approach. |

### South and Central Hood Canal

| Station | Name | Type | Lat | Lon | Reference | App note |
| --- | --- | --- | ---: | ---: | --- | --- |
| `9445133` | Bangor Wharf | R | 47.7483 | -122.7270 |  | Station-backed north/central Hood Canal candidate. |
| `9445246` | Whitney Point, Dabob Bay | S | 47.7617 | -122.8500 | `9447130` | Dabob Bay candidate; north of strict South Hood Canal. |
| `9445269` | Zelatched Point, Dabob Bay | S | 47.7117 | -122.8220 | `9447130` | Dabob Bay candidate. |
| `9445272` | Quilcene, Quilcene Bay, Dabob Bay | S | 47.8000 | -122.8580 | `9447130` | Northern edge candidate for broader Hood Canal coverage. |
| `9445293` | Pleasant Harbor | S | 47.6650 | -122.9120 | `9447130` | Mid-canal west shore candidate. |
| `9445303` | Seabeck, Seabeck Bay | S | 47.6417 | -122.8280 | `9447130` | Useful for Seabeck and east shore. |
| `9445326` | Triton Head | S | 47.6033 | -122.9820 | `9447130` | Good south/central canal west-shore candidate. |
| `9445388` | Ayock Point | S | 47.5083 | -123.0520 | `9447130` | Useful south Hood Canal candidate. |
| `9445441` | Lynch Cove Dock | S | 47.4183 | -122.9000 | `9447130` | Important for Lynch Cove/Belfair end. |
| `9445478` | Union | R | 47.3583 | -123.0980 |  | Station-backed south Hood Canal anchor. |

### South Puget Sound, Tacoma Narrows, Gig Harbor, Inlets

| Station | Name | Type | Lat | Lon | Reference | App note |
| --- | --- | --- | ---: | ---: | --- | --- |
| `9446248` | Des Moines, East Passage | S | 47.4000 | -122.3280 | `9447130` | North boundary for East Passage/Vashon approach. |
| `9446281` | Allyn, Case Inlet | S | 47.3833 | -122.8230 | `9447130` | Case Inlet/Allyn candidate. |
| `9446291` | Wauna, Carr Inlet | R | 47.3783 | -122.6340 |  | Station-backed Carr Inlet/Purdy candidate. |
| `9446366` | Vaughn, Case Inlet | S | 47.3417 | -122.7750 | `9447130` | Case Inlet candidate. |
| `9446369` | Gig Harbor | S | 47.3400 | -122.5880 | `9447130` | Local harbor tide candidate, but not station-backed. |
| `9446375` | Tahlequah, Neil Pt., Dalco Passage, Vashon I. | S | 47.3333 | -122.5070 | `9447130` | Dalco/Vashon/Southworth candidate. |
| `9446451` | Horsehead Bay, Carr Inlet | S | 47.3017 | -122.6820 | `9447130` | Carr Inlet west-shore candidate. |
| `9446484` | Tacoma, Commencement Bay, Sitcum Waterway | R | 47.2667 | -122.4133 |  | Primary station-backed Tacoma/Gig Harbor tide anchor. |
| `9446486` | Tacoma Narrows Bridge | S | 47.2717 | -122.5520 | `9447130` | Better local tide candidate for Narrows-specific regions. |
| `9446489` | Walkers Landing, Pickering Passage | S | 47.2817 | -122.9230 | `9447130` | Pickering Passage candidate. |
| `9446491` | Arletta, Hale Passage | S | 47.2800 | -122.6520 | `9447130` | Hale Passage/Fox Island candidate. |
| `9446500` | Home, Von Geldern Cove, Carr Inlet | S | 47.2750 | -122.7580 | `9447130` | Carr Inlet/Home candidate. |
| `9446583` | McMicken Island, Case Inlet | S | 47.2467 | -122.8620 | `9447130` | Case Inlet/South Sound candidate. |
| `9446628` | Shelton, Oakland Bay | S | 47.2150 | -123.0830 | `9447130` | Oakland Bay/Shelton candidate. |
| `9446638` | Longbranch, Filucy Bay | S | 47.2100 | -122.7530 | `9447130` | Key Peninsula/Filucy Bay candidate. |
| `9446666` | Arcadia, Totten Inlet | S | 47.1967 | -122.9380 | `9447130` | Totten Inlet candidate. |
| `9446671` | Devils Head, Drayton Passage | S | 47.1667 | -122.7630 | `9447130` | Drayton Passage candidate. |
| `9446705` | Yoman Point, Anderson Island, Balch Passage | R | 47.1800 | -122.6750 |  | Station-backed Balch/Anderson candidate. |
| `9446714` | Steilacoom, Cormorant Passage | S | 47.1733 | -122.6030 | `9447130` | Steilacoom/Cormorant candidate. |
| `9446742` | Barron Point, Little Skookum Inlet Entrance | S | 47.1567 | -123.0080 | `9447130` | Little Skookum/Hammersley approach candidate. |
| `9446752` | Henderson Inlet | S | 47.1550 | -122.8380 | `9447130` | Henderson Inlet candidate. |
| `9446800` | Dofflemeyer Point, Boston Hbr., Budd Inlet | S | 47.1417 | -122.9030 | `9447130` | Budd Inlet/Boston Harbor candidate. |
| `9446804` | Sandy Point Anderson Island, Puget Sound | R | 47.1530 | -122.6751 |  | Station-backed Anderson Island/South Sound anchor. |
| `9446807` | Budd Inlet, Olympia Shoal | R | 47.0983 | -122.8950 |  | Station-backed Olympia/Budd Inlet anchor. |
| `9446828` | Dupont Wharf, Nisqually Reach | S | 47.1183 | -122.6650 | `9447130` | Nisqually Reach/Dupont candidate. |
| `9446969` | Olympia, Budd Inlet | S | 47.0600 | -122.9030 | `9447130` | Inner Olympia candidate. |

## Current-Prediction Stations

### Central Kitsap, Port Orchard, Bremerton, Rich Passage

| Station | Name | Type | Lat | Lon | Bins/depths | App note |
| --- | --- | --- | ---: | ---: | --- | --- |
| `PUG1508` | Liberty Bay (entrance), Port Orchard | H | 47.7068 | -122.6283 | `1@37ft`, `5@24ft`, `10@7ft` | Best Liberty Bay/Poulsbo current candidate. |
| `PCT1651` | Port Orchard, off Keyport | W | 47.7003 | -122.6083 | `1` | Weak/variable; use cautiously if at all. |
| `PUG1510` | Port Washington Narrows, Warren Ave. Bridge | H | 47.5796 | -122.6307 | `1@21ft`, `6@4ft` | Best Bremerton/Silverdale narrows candidate. |
| `ks0101` | Rich Passage, LB 8 | H | 47.5933 | -122.5426 | `1@11.2ft`, `2@14.4ft`, `7@30.8ft` | Rich Passage alternate. |
| `PUG1513` | Rich Passage, East end | H | 47.5700 | -122.5298 | `1@70ft`, `6@38ft`, `10@11ft` | East Rich Passage/Manchester candidate. |
| `PUG1514` | Rich Passage, West end | H | 47.5899 | -122.5623 | `1@57ft`, `5@31ft`, `8@12ft` | West Rich Passage/Port Orchard candidate. |
| `PCT1701` | Off Pleasant Beach | S | 47.5833 | -122.5333 | `1` | Useful if adding Pleasant Beach/Blake Island spots. |
| `PCT1711` | Port Orchard, southwest of Waterman | W | 47.5667 | -122.6000 | `1` | Weak/variable; likely not a primary scoring anchor. |
| `PUG1517` | Blake Island, S of | H | 47.5203 | -122.4879 | `8@172ft`, `16@93ft`, `21@44ft` | Colvos/Rich Passage exposure candidate. |
| `PUG1518` | Anderson Point, East of, Colvos Passage | H | 47.4394 | -122.5258 | `10@154ft`, `17@62ft`, `19@35ft` | Colvos Passage candidate. |
| `PUG1519` | Point Richmond, East of, Colvos Passage | H | 47.3766 | -122.5287 | `3@241ft`, `13@110ft`, `18@44ft` | Lower Colvos/South Vashon candidate. |
| `PUG1520` | Dolphin Point, 1.3 miles East of | H | 47.5015 | -122.4236 | `28@139ft`, `35@48ft` | East Passage/Vashon candidate. |

### South and Central Hood Canal

| Station | Name | Type | Lat | Lon | Bins/depths | App note |
| --- | --- | --- | ---: | ---: | --- | --- |
| `ks0201` | Bangor, Hood Canal LB B | H | 47.7578 | -122.7306 | `2@14ft`, `6@28ft`, `10@41ft` | Bangor/central Hood Canal candidate. |
| `PUG1601` | Hazel Point | H | 47.6912 | -122.7628 | `1@154ft`, `11@88ft`, `21@23ft` | Best lower-mid Hood Canal current candidate from available list. |
| `PUG1602` | South Point | H | 47.8217 | -122.6767 | `1@178ft`, `42@43ft`, `48@24ft` | North of the South Hood core; useful broader canal boundary. |
| `PUG1603` | Hood Canal Bridge | H | 47.8547 | -122.6294 | `1@209ft`, `11@111ft`, `20@22ft` | North boundary and bridge-specific current candidate. |
| `PCT1596` | Chinom Point | W | 47.5333 | -123.0333 | `1` | Weak/variable; may help label uncertainty near Ayock/Triton only. |

### South Puget Sound, Tacoma Narrows, Gig Harbor, Inlets

| Station | Name | Type | Lat | Lon | Bins/depths | App note |
| --- | --- | --- | ---: | ---: | --- | --- |
| `PUG1521` | Browns Point, 1.6 miles North of | H | 47.3287 | -122.4540 | `14@290ft`, `24@159ft`, `34@28ft` | Commencement Bay/Browns Point candidate. |
| `PUG1522` | Dalco Passage | H | 47.3251 | -122.5247 | `3@187ft`, `12@128ft` | Dalco Passage/Tahlequah candidate. |
| `PUG1523` | Gig Harbor Entrance | H | 47.3242 | -122.5719 | `1@54ft`, `8@31ft`, `14@11ft` | Best Gig Harbor entrance-specific current candidate. |
| `PUG1524` | The Narrows, North end - midstream | H | 47.3060 | -122.5500 | `1@139ft`, `9@87ft`, `16@40ft` | Narrows north candidate. |
| `PUG1526` | The Narrows, North End (west side) | H | 47.3040 | -122.5567 | `5@193ft`, `20@95ft`, `28@42ft` | Narrows west-side candidate. |
| `PUG1527` | The Narrows, 0.3 miles North of Bridge | H | 47.2743 | -122.5453 | `1@141ft`, `12@69ft`, `19@23ft` | Current TideWindow Gig Harbor/Tacoma Narrows anchor. |
| `PUG1528` | The Narrows, South end (midstream) | H | 47.2613 | -122.5583 | `1@131ft`, `13@52ft`, `17@26ft` | Narrows south candidate. |
| `PUG1529` | Hale Passage, East end | H | 47.2479 | -122.5956 | `1@77ft`, `6@44ft`, `11@11ft` | Fox Island/Hale Passage east candidate. |
| `PUG1530` | Hale Passage, West end | H | 47.2814 | -122.6631 | `1@70ft`, `10@40ft`, `18@14ft` | Fox Island/Hale Passage west candidate. |
| `PUG1531` | Gibson Point, 0.8 miles East of | H | 47.2191 | -122.5887 | `6@149ft`, `13@81ft`, `18@31ft` | Anderson Island/Gibson Point candidate. |
| `PUG1532` | Steilacoom, 0.8 miles North of | H | 47.1824 | -122.6056 | `6@177ft`, `13@85ft`, `16@45ft` | Steilacoom/Cormorant Passage candidate. |
| `PUG1533` | Ketron Island, West of | H | 47.1486 | -122.6594 | `10@143ft`, `14@90ft`, `18@38ft` | Ketron/Anderson candidate. |
| `PUG1534` | Nisqually Reach, 0.5 miles South of Lyle Point | H | 47.1169 | -122.6989 | `1@177ft`, `12@68ft`, `16@29ft` | Nisqually Reach candidate. |
| `PUG1535` | Balch Passage, NE of Eagle Island | H | 47.1906 | -122.6916 | `1@60ft`, `10@30ft`, `16@11ft` | Balch Passage candidate. |
| `PUG1536` | Pitt Passage, NE of Pitt Island | H | 47.2238 | -122.7114 | `1@23ft`, `6@7ft` | Pitt Passage candidate. |
| `PUG1537` | Drayton Passage | H | 47.1726 | -122.7415 | `5@118ft`, `15@52ft`, `20@19ft` | Drayton Passage candidate. |
| `PUG1538` | Devils Head, West of | H | 47.1607 | -122.7894 | `5@191ft`, `16@83ft`, `22@24ft` | Case Inlet/Drayton boundary candidate. |
| `PUG1539` | Dana Passage | H | 47.1631 | -122.8681 | `1@88ft`, `8@43ft`, `12@16ft` | Dana Passage candidate. |
| `PUG1540` | Budd Inlet Entrance | H | 47.1402 | -122.9214 | `1@71ft`, `7@32ft`, `10@12ft` | Olympia/Budd Inlet current anchor. |
| `PUG1541` | Peale Passage, South end | H | 47.1749 | -122.8870 | `1@35ft`, `5@22ft`, `9@9ft` | Peale Passage candidate. |
| `PUG1542` | Peale Passage, North end | H | 47.2175 | -122.9146 | `1@17ft`, `5@4ft` | Peale Passage candidate. |
| `PUG1543` | Squaxin Passage, North of Hunter Point | H | 47.1763 | -122.9190 | `1@32ft`, `5@18ft`, `9@5ft` | Squaxin Passage candidate. |
| `PUG1544` | Totten Inlet Entrance | H | 47.1883 | -122.9454 | `3@67ft`, `7@41ft`, `11@14ft` | Totten Inlet candidate. |
| `PUG1545` | Libby Point, Hammersley Inlet | H | 47.1989 | -122.9890 | `1@19ft`, `10@5ft` | Hammersley Inlet candidate. |
| `PUG1546` | Pickering Passage, West of Squaxin Island | H | 47.2193 | -122.9345 | `1@52ft`, `8@29ft`, `14@9ft` | Pickering Passage west candidate. |
| `PUG1547` | Pickering Passage, off Graham Point | H | 47.2472 | -122.9259 | `1@59ft`, `10@30ft`, `16@10ft` | Pickering Passage central candidate. |
| `PUG1548` | Pickering Passage, North end | H | 47.3057 | -122.8509 | `1@78ft`, `6@45ft`, `10@19ft` | Pickering Passage north candidate. |
| `PCT1861` | Eld Inlet entrance | S | 47.1463 | -122.9333 | `1@15ft` | Eld Inlet subordinate candidate. |
| `PCT1896` | Hammersley Inlet, west of Skookum Point | S | 47.2070 | -123.0395 | `1@15ft` | Hammersley west candidate. |
| `PCT1916` | Case Inlet, 1 mile SE of McMicken Island | W | 47.2383 | -122.8437 | `1` | Weak/variable; use only with clear uncertainty label. |

## Stations To Be Careful With

- Weak/variable current stations (`W`) are not ideal for TideWindow scoring because NOAA labels them as weak/variable current locations. They can still be useful for "low current expected" context, but confidence should drop or the UI should label the assumption.
- Some tide-prediction stations are subordinate to Seattle (`9447130`). They may be locally named and useful for timing, but they are not the same as local real-time water-level stations.
- South Hood Canal has useful tide stations, but current-prediction coverage is less dense than Tacoma Narrows/South Sound. Regions like Union, Lynch Cove, Belfair, and Ayock should start with conservative confidence labels.

## Sources

- NOAA CO-OPS metadata API: `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=tidepredictions`
- NOAA CO-OPS metadata API: `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=currentpredictions`
- NOAA CO-OPS metadata API: `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=waterlevels`
- NOAA current station list for Puget Sound current survey stations: `https://tidesandcurrents.noaa.gov/cdata/StationList?filter=historic&keyword=pug&type=Current+Data`
- NOAA current predictions: `https://tidesandcurrents.noaa.gov/noaacurrents/index.html`
- NOAA tide predictions: `https://tidesandcurrents.noaa.gov/stations.html?type=Tide+Predictions`

## App Sequence

Done:

- Added `ProviderContext` selection per region with explicit `tide_station`, `current_station`, and current `bin`.
- Added the first South Sound regions while current coverage is dense and harmonic (`H`): Tacoma Narrows, Carr Inlet, Case Inlet, Anderson Island, Steilacoom/Nisqually, and Olympia/Budd Inlet.

Next:

1. Add a provider-debug panel in the UI so each region shows exactly which tide station, current station, and current bin/depth are being used.
2. Add South Hood Canal after the app has confidence labels per station type, because several current candidates are sparse or weak/variable.
3. Add Aberdeen after selecting coastal stations and a different confidence profile from the inland Puget Sound regions.
