// Queensland suburbs — sourced from Wikipedia LGA suburb lists (City of Brisbane, Moreton Bay,
// Logan City, City of Ipswich, Redland City, City of Gold Coast, Sunshine Coast Region, Noosa
// Shire, Scenic Rim, Somerset Region, Lockyer Valley Region) plus regional QLD cities.
// Last verified: June 2026.
//
// Duplicates removed: "Kenmore Hills" (was in two Brisbane groups), "Nambour" (SC only).

export const SUBURB_CATEGORIES = [
  // ─────────────────────────────────────────────────────────────────────────────
  // CITY OF BRISBANE  (194 suburbs / localities total)
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Brisbane — Inner City",
    suburbs: [
      "Bowen Hills", "Brisbane City", "East Brisbane", "Fortitude Valley",
      "Herston", "Highgate Hill", "Kangaroo Point", "Kelvin Grove",
      "New Farm", "Newstead", "Paddington", "Petrie Terrace", "Red Hill",
      "South Brisbane", "Spring Hill", "Teneriffe", "West End", "Woolloongabba",
    ],
  },
  {
    category: "Brisbane — Northern Suburbs",
    suburbs: [
      "Albion", "Alderley", "Ascot", "Aspley", "Bald Hills", "Banyo",
      "Boondall", "Bracken Ridge", "Bridgeman Downs", "Brighton",
      "Brisbane Airport", "Carseldine", "Chermside", "Chermside West",
      "Clayfield", "Deagon", "Eagle Farm", "Everton Park", "Ferny Grove",
      "Fitzgibbon", "Gaythorne", "Geebung", "Gordon Park", "Grange",
      "Hamilton", "Hendra", "Kalinga", "Kedron", "Keperra", "Lutwyche",
      "McDowall", "Mitchelton", "Newmarket", "Northgate", "Nudgee",
      "Nudgee Beach", "Nundah", "Pinkenba", "Sandgate", "Shorncliffe",
      "Stafford", "Stafford Heights", "Taigum", "Virginia", "Wavell Heights",
      "Wilston", "Windsor", "Wooloowin", "Zillmere",
    ],
  },
  // {
  //   category: "Brisbane — Southern Suburbs",
  //   suburbs: [
  //     "Acacia Ridge", "Algester", "Annerley", "Archerfield", "Burbank",
  //     "Calamvale", "Coopers Plains", "Darra", "Doolandella", "Drewvale",
  //     "Durack", "Dutton Park", "Eight Mile Plains", "Ellen Grove", "Fairfield",
  //     "Forest Lake", "Greenslopes", "Heathwood", "Holland Park",
  //     "Holland Park West", "Inala", "Karawatha", "Kuraby", "Larapinta",
  //     "MacGregor", "Mackenzie", "Mansfield", "Moorooka", "Mount Gravatt",
  //     "Mount Gravatt East", "Nathan", "Pallara", "Parkinson", "Richlands",
  //     "Robertson", "Rochedale", "Rocklea", "Runcorn", "Salisbury",
  //     "Stones Corner", "Stretton", "Sumner", "Sunnybank", "Sunnybank Hills",
  //     "Tarragindi", "Tennyson", "Upper Mount Gravatt", "Wacol", "Willawong",
  //     "Wishart", "Yeerongpilly", "Yeronga",
  //   ],
  // },
  {
    category: "Brisbane — Eastern & Bayside",
    suburbs: [
      "Balmoral", "Belmont", "Bulimba", "Camp Hill", "Cannon Hill",
      "Carina", "Carina Heights", "Carindale", "Chandler", "Coorparoo",
      "Gumdale", "Hawthorne", "Hemmant", "Lota", "Lytton", "Manly",
      "Manly West", "Morningside", "Murarrie", "Norman Park",
      "Port of Brisbane", "Ransome", "Seven Hills", "Tingalpa", "Wakerley",
      "Wynnum", "Wynnum West",
    ],
  },
  {
    category: "Brisbane — Western Suburbs",
    suburbs: [
      "Anstead", "Ashgrove", "Auchenflower", "Banks Creek", "Bardon",
      "Bellbowrie", "Brookfield", "Chapel Hill", "Chelmer", "Chuwar",
      "Corinda", "England Creek", "Enoggera", "Enoggera Reservoir",
      "Fig Tree Pocket", "Graceville", "Indooroopilly", "Jamboree Heights",
      "Jindalee", "Karana Downs", "Kenmore", "Kenmore Hills", "Kholo",
      "Lake Manchester", "Middle Park", "Milton", "Moggill", "Mount Coot-tha",
      "Mount Crosby", "Mount Ommaney", "Oxley", "Pinjarra Hills", "Pullenvale",
      "Riverhills", "Seventeen Mile Rocks", "Sherwood", "Sinnamon Park",
      "St Lucia", "Taringa", "The Gap", "Toowong", "Upper Brookfield",
      "Upper Kedron", "Westlake",
    ],
  },
  {
    category: "Brisbane — Moreton Island",
    suburbs: [
      "Bulwer", "Cowan Cowan", "Kooringal", "Moreton Island",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // MORETON BAY REGION
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Moreton Bay — Urban",
    suburbs: [
      "Albany Creek", "Arana Hills", "Banksia Beach", "Beachmere", "Bellara",
      "Bongaree", "Bray Park", "Brendale", "Bunya", "Burpengary",
      "Caboolture", "Caboolture South", "Cashmere", "Clontarf", "Dakabin",
      "Deception Bay", "Eatons Hill", "Elimbah", "Everton Hills", "Ferny Hills",
      "Godwin Beach", "Griffin", "Joyner", "Kallangur", "Kippa-Ring",
      "Kurwongbah", "Lawnton", "Mango Hill", "Margate", "Moodlu",
      "Morayfield", "Murrumba Downs", "Narangba", "Newport", "Ningi",
      "North Lakes", "Petrie", "Redcliffe", "Rothwell", "Sandstone Point",
      "Scarborough", "Strathpine", "Upper Caboolture", "Warner", "Whiteside",
      "Woody Point", "Woorim",
    ],
  },
  {
    category: "Moreton Bay — Hinterland",
    suburbs: [
      "Armstrong Creek", "Bellmere", "Bellthorpe", "Booroobin", "Bracalba",
      "Camp Mountain", "Campbells Pocket", "Cedar Creek", "Cedarton",
      "Clear Mountain", "Closeburn", "Commissioners Flat", "D'Aguilar",
      "Dayboro", "Delaneys Creek", "Donnybrook", "Draper", "Greenstone",
      "Highvale", "Jollys Lookout", "King Scrub", "Kobble Creek",
      "Laceys Creek", "Meldale", "Moorina", "Mount Delaney", "Mount Glorious",
      "Mount Mee", "Mount Nebo", "Mount Pleasant", "Mount Samson", "Neurum",
      "Ocean View", "Rocksberg", "Rush Creek", "Samford Valley",
      "Samford Village", "Samsonvale", "Stanmore", "Stony Creek", "Toorbul",
      "Wamuran", "Wamuran Basin", "Welsby", "White Patch", "Wights Mountain",
      "Woodford", "Yugar",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // LOGAN CITY
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Logan City",
    suburbs: [
      "Bahrs Scrub", "Bannockburn", "Beenleigh", "Belivah", "Berrinba",
      "Bethania", "Boronia Heights", "Browns Plains", "Buccan", "Carbrook",
      "Cedar Creek", "Cedar Grove", "Cedar Vale", "Chambers Flat", "Cornubia",
      "Crestmead", "Daisy Hill", "Eagleby", "Edens Landing", "Forestdale",
      "Greenbank", "Heritage Park", "Hillcrest", "Holmview", "Jimboomba",
      "Kagaru", "Kingston", "Logan Central", "Logan Reserve", "Logan Village",
      "Loganholme", "Loganlea", "Lyons", "Marsden", "Meadowbrook",
      "Mount Warren Park", "Mundoolun", "Munruben", "New Beith",
      "North Maclean", "Park Ridge", "Park Ridge South", "Priestdale",
      "Regents Park", "Rochedale South", "Shailer Park", "Slacks Creek",
      "South Maclean", "Springwood", "Stockleigh", "Tamborine", "Tanah Merah",
      "Underwood", "Undullah", "Veresdale", "Veresdale Scrub", "Waterford",
      "Waterford West", "Windaroo", "Wolffdene", "Woodhill", "Woodridge",
      "Yarrabilba",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // CITY OF IPSWICH
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Ipswich — Urban",
    suburbs: [
      "Augustine Heights", "Barellan Point", "Basin Pocket", "Bellbird Park",
      "Blacksoil", "Blackstone", "Booval", "Brassall", "Brookwater",
      "Bundamba", "Camira", "Carole Park", "Churchill", "Chuwar", "Coalfalls",
      "Collingwood Park", "Dinmore", "East Ipswich", "Eastern Heights",
      "Ebbw Vale", "Flinders View", "Gailes", "Goodna", "Ipswich",
      "Karalee", "Karrabin", "Leichhardt", "Moores Pocket", "Muirlea",
      "New Chum", "Newtown", "North Booval", "North Ipswich", "North Tivoli",
      "One Mile", "Raceview", "Redbank", "Redbank Plains", "Riverview",
      "Sadliers Crossing", "Silkstone", "Springfield", "Springfield Central",
      "Springfield Lakes", "Tivoli", "West Ipswich", "Woodend", "Wulkuraka",
      "Yamanto",
    ],
  },
  {
    category: "Ipswich — Rural",
    suburbs: [
      "Amberley", "Ashwell", "Calvert", "Deebing Heights", "Ebenezer",
      "Goolman", "Grandchester", "Haigslea", "Ironbark", "Jeebropilly",
      "Lanefield", "Marburg", "Mount Forbes", "Mount Marrow", "Mutdapilly",
      "Pine Mountain", "Purga", "Ripley", "Rosewood", "South Ripley",
      "Spring Mountain", "Swanbank", "Tallegalla", "Thagoona", "The Bluff",
      "Walloon", "White Rock", "Willowbank", "Woolshed",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // REDLAND CITY
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Redland City",
    suburbs: [
      "Alexandra Hills", "Amity Point", "Birkdale", "Capalaba", "Cleveland",
      "Coochiemudlo Island", "Dunwich", "Karragarra Island", "Lamb Island",
      "Macleay Island", "Mount Cotton", "North Stradbroke Island", "Ormiston",
      "Point Lookout", "Redland Bay", "Russell Island", "Sheldon",
      "Thornlands", "Thornside", "Victoria Point", "Wellington Point",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // SCENIC RIM REGION
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Scenic Rim",
    suburbs: [
      // Beaudesert sub-region
      "Beaudesert", "Beechmont", "Benobble", "Biddaddaba", "Birnam",
      "Boyland", "Bromelton", "Canungra", "Christmas Creek", "Cryna",
      "Gleneagle", "Hillview", "Innisplain", "Josephville", "Kerry",
      "Kooralbyn", "Lamington National Park", "Laravale", "Palen Creek",
      "Rathdowney", "Tabragalba", "Tamborine Mountain", "Tamrookum",
      "Tamrookum Creek", "Witheren", "Wonglepong",
      // Boonah sub-region
      "Aratula", "Boonah", "Charlwood", "Fassifern", "Harrisville", "Kalbar",
      "Maroon", "Moogerah", "Mount Alford", "Mount Walker", "Roadvale",
      "Rosevale", "Tarome", "Templin", "Warrill View",
      // Other localities
      "Allandale", "Allenview", "Barney View", "Binna Burra", "Bunjurgen",
      "Cainbable", "Carneys Creek", "Clumber", "Coleyville", "Croftby",
      "Dugandan", "Fassifern Valley", "Flying Fox", "Hoya", "Illinbah",
      "Kents Pocket", "Kulgun", "Limestone Ridges", "Lower Mount Walker",
      "Milbong", "Milford", "Milora", "Moorang", "Morwincha", "Mount Barney",
      "Mount French", "Mount Lindesay", "Mount Walker West", "Munbilla",
      "Nindooinbah", "North Tamborine", "O'Reilly", "Peak Crossing",
      "Running Creek", "Sarabah", "Teviotville", "Wilsons Plains",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // SOMERSET REGION
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Somerset Region",
    suburbs: [
      "Borallon", "Caboonbah", "Clarendon", "Colinton", "Coolana",
      "Coominya", "Dundas", "Esk", "Fairney View", "Fernvale",
      "Glamorgan Vale", "Glenfern", "Harlin", "Hazeldean", "Jimna",
      "Kilcoy", "Lake Somerset", "Lake Wivenhoe", "Lark Hill", "Linville",
      "Lowood", "Minden", "Monsildale", "Moore", "Mount Hallen",
      "Mount Tarampa", "Prenzlau", "Rifle Range", "Tarampa", "Toogoolawah",
      "Vernor", "Villeneuve", "Wanora", "Winya", "Wivenhoe Pocket",
      "Woolmar", "Yimbun",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // LOCKYER VALLEY REGION
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Lockyer Valley",
    suburbs: [
      "Adare", "Atkinsons Dam", "Biarra", "Blenheim", "Blanchview",
      "Brightview", "Buaraba", "Caffey", "Churchable", "College View",
      "Cressbrook", "Crowley Vale", "Flagstone Creek", "Forest Hill",
      "Fordsdale", "Gatton", "Glen Cairn", "Glenore Grove", "Grandchester",
      "Grantham", "Hatton Vale", "Helidon", "Helidon Spa", "Ingoldsby",
      "Iredale", "Junction View", "Kensington Grove", "Kentville",
      "Laidley", "Laidley Heights", "Laidley North", "Laidley South",
      "Lake Clarendon", "Lawes", "Lockrose", "Lockyer", "Lockyer Waters",
      "Lower Tenthill", "Ma Ma Creek", "Marburg", "Morton Vale",
      "Mount Berryman", "Mount Sylvia", "Mount Whitestone", "Mulgowie",
      "Murphys Creek", "Patrick Estate", "Placid Hills", "Plainland",
      "Postmans Ridge", "Preston", "Regency Downs", "Ringwood", "Rockmount",
      "Rockside", "Ropeley", "Sandy Creek", "Silver Ridge", "Somerset Dam",
      "Spring Creek", "Stockyard", "Summerholm", "Thornton", "Townson",
      "Upper Flagstone", "Upper Lockyer", "Upper Tenthill", "Veradilla",
      "Vinegar Hill", "West Haldon", "White Mountain", "Winwill", "Withcott",
      "Wivenhoe Hill", "Woodbine", "Woodlands",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // CITY OF GOLD COAST
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Gold Coast — Suburbs",
    suburbs: [
      "Arundel", "Ashmore", "Benowa", "Biggera Waters", "Bilinga",
      "Broadbeach", "Broadbeach Waters", "Bundall", "Burleigh Heads",
      "Burleigh Waters", "Carrara", "Clear Island Waters", "Coolangatta",
      "Coombabah", "Coomera", "Currumbin", "Currumbin Waters", "Elanora",
      "Helensvale", "Highland Park", "Hollywell", "Hope Island", "Jacobs Well",
      "Labrador", "Main Beach", "Mermaid Beach", "Mermaid Waters", "Merrimac",
      "Miami", "Molendinar", "Mudgeeraba", "Nerang", "Neranwood", "Ormeau",
      "Oxenford", "Pacific Pines", "Palm Beach", "Paradise Point", "Parkwood",
      "Pimpama", "Reedy Creek", "Robina", "Runaway Bay", "Southport",
      "Surfers Paradise", "Tallai", "Tallebudgera", "Tugun", "Upper Coomera",
      "Varsity Lakes", "Worongary", "Yatala",
    ],
  },
  {
    category: "Gold Coast — Hinterland & Localities",
    suburbs: [
      "Advancetown", "Alberton", "Austinville", "Bonogin", "Cedar Creek",
      "Clagiraba", "Currumbin Valley", "Gaven", "Gilberton", "Gilston",
      "Guanaba", "Kingsholme", "Lower Beechmont", "Luscombe", "Maudsland",
      "Mount Nathan", "Natural Bridge", "Norwell", "Numinbah Valley",
      "Ormeau Hills", "South Stradbroke", "Springbrook", "Stapylton",
      "Steiglitz", "Tallebudgera Valley", "Willow Vale", "Wongawallan",
      "Woongoolba",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // SUNSHINE COAST REGION
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Sunshine Coast — Caloundra & Kawana",
    suburbs: [
      "Aroona", "Battery Hill", "Beerburrum", "Beerwah", "Bells Creek",
      "Birtinya", "Bokarina", "Bribie Island North", "Buddina", "Caloundra",
      "Caloundra West", "Cambroon", "Conondale", "Coochin Creek",
      "Crohamhurst", "Curramore", "Currimundi", "Diamond Valley", "Dicky Beach",
      "Elaman Creek", "Glass House Mountains", "Glenview", "Golden Beach",
      "Harper Creek", "Kings Beach", "Landsborough", "Little Mountain",
      "Maleny", "Meridan Plains", "Minyama", "Moffat Beach", "Mooloolah Valley",
      "Mount Mellum", "Nirimba", "North Maleny", "Palmview", "Parrearra",
      "Peachester", "Pelican Waters", "Reesville", "Shelly Beach", "Warana",
      "Witta", "Wootha", "Wurtulla",
    ],
  },
  {
    category: "Sunshine Coast — Maroochydore, Buderim & Nambour",
    suburbs: [
      "Alexandra Headland", "Bald Knob", "Balmoral Ridge", "Belli Park",
      "Bli Bli", "Bridges", "Buderim", "Burnside", "Chevallum", "Coes Creek",
      "Coolabine", "Cooloolabin", "Coolum Beach", "Cotton Tree", "Diddillibah",
      "Doonan", "Dulong", "Eerwah Vale", "Eudlo", "Eumundi", "Flaxton",
      "Forest Glen", "Gheerulla", "Highworth", "Hunchy", "Ilkley",
      "Image Flat", "Kenilworth", "Kiamba", "Kidaman Creek", "Kiels Mountain",
      "Kulangoor", "Kuluin", "Kunda Park", "Kureelpa", "Landers Shoot",
      "Mapleton", "Marcoola", "Maroochy River", "Maroochydore", "Mons",
      "Montville", "Mooloolaba", "Mount Coolum", "Mountain Creek", "Mudjimba",
      "Nambour", "Ninderry", "North Arm", "Obi Obi", "Pacific Paradise",
      "Palmwoods", "Parklands", "Peregian Beach", "Peregian Springs",
      "Perwillowen", "Point Arkwright", "Rosemount", "Sippy Downs", "Tanawha",
      "Towen Mountain", "Twin Waters", "Valdora", "Verrierdale",
      "West Woombye", "Weyba Downs", "Woombye", "Yandina", "Yandina Creek",
      "Yaroomba",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // NOOSA SHIRE
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Noosa",
    suburbs: [
      // Urban suburbs
      "Noosa Heads", "Noosaville", "Sunrise Beach", "Sunshine Beach",
      "Tewantin",
      // Localities
      "Boreen Point", "Cooroy", "Cooroy Mountain", "Cootharaba", "Federal",
      "Kin Kin", "Lake Cootharaba", "Lake MacDonald", "Pomona",
      "Ringtail Creek", "Ringtail Forest",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // GYMPIE REGION
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Gympie Region",
    suburbs: [
      "Gympie", "Southside", "Tin Can Bay", "Rainbow Beach", "Cooloola Cove",
      "Imbil", "Kandanga", "Kilkivan", "Murgon", "Nanango", "Kingaroy",
      "Wondai", "Proston", "Blackbutt", "Yarraman",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // FRASER COAST REGION  (Hervey Bay / Maryborough)
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Fraser Coast — Hervey Bay",
    suburbs: [
      "Hervey Bay", "Urangan", "Pialba", "Scarness", "Torquay", "Eli Waters",
      "Point Vernon", "Kawungan", "Craignish", "Nikenbah", "Wondunna",
      "Booral", "Dundowran", "Dundowran Beach", "Howard", "Burrum Heads",
      "Toogoom",
    ],
  },
  {
    category: "Fraser Coast — Maryborough & Wide Bay",
    suburbs: [
      "Maryborough", "Granville", "Tinana", "Tiaro", "Gundiah",
      "Childers", "Isis", "Biggenden", "Gin Gin", "Mundubbera", "Gayndah",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // BUNDABERG REGION
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Bundaberg Region",
    suburbs: [
      "Bundaberg", "Bundaberg North", "Bundaberg South", "Bundaberg East",
      "Bundaberg West", "Kepnock", "Avoca", "Avenell Heights", "Svensson Heights",
      "Millbank", "Ashfield", "Thabeban", "Kensington", "Norville",
      "Bargara", "Elliott Heads", "Moore Park Beach", "Burnett Heads",
      "Innes Park", "Coral Cove", "Agnes Water", "Seventeen Seventy",
      "Gin Gin", "Childers", "Biggenden",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // TOOWOOMBA REGION & DARLING DOWNS
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Toowoomba — City",
    suburbs: [
      "Toowoomba", "Drayton", "Harristown", "Kearneys Spring", "Newtown",
      "North Toowoomba", "South Toowoomba", "East Toowoomba", "Rockville",
      "Centenary Heights", "Middle Ridge", "Rangeville", "Wilsonton",
      "Wilsonton Heights", "Mount Lofty", "Glenvale", "Darling Heights",
      "Clifton", "Cranley", "Wyalla Plaza", "Westbrook", "Highfields",
      "Kleinton", "Oakey", "Pittsworth",
    ],
  },
  {
    category: "Darling Downs & South West QLD",
    suburbs: [
      "Dalby", "Miles", "Roma", "Goondiwindi", "Warwick", "Stanthorpe",
      "Inglewood", "Condamine", "Mitchell", "Charleville", "Cunnamulla",
      "St George", "Surat", "Chinchilla", "Tara", "Millmerran",
      "Clifton", "Allora", "Killarney",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // ROCKHAMPTON & CENTRAL QLD
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Rockhampton Region",
    suburbs: [
      "Rockhampton", "North Rockhampton", "Gracemere", "Allenstown",
      "Berserker", "Frenchville", "Norman Gardens", "Park Avenue",
      "Kawana", "Mount Morgan", "Yeppoon", "Emu Park", "Zilzie",
      "Byfield", "Marlborough", "Emerald", "Blackwater", "Springsure",
      "Clermont", "Alpha", "Barcaldine",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // GLADSTONE REGION
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Gladstone Region",
    suburbs: [
      "Gladstone", "West Gladstone", "South Gladstone", "Barney Point",
      "New Auckland", "Toolooa", "Kin Kora", "Clinton", "Sun Valley",
      "Boyne Island", "Tannum Sands", "Calliope", "Agnes Water",
      "Seventeen Seventy", "Biloela", "Moura", "Banana",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // MACKAY REGION & WHITSUNDAYS
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Mackay Region",
    suburbs: [
      "Mackay", "North Mackay", "South Mackay", "East Mackay", "West Mackay",
      "Rural View", "Ooralea", "Paget", "Glenella", "Mount Pleasant",
      "Andergrove", "Blacks Beach", "Eimeo", "Bucasia", "Farleigh",
      "Sarina", "Mirani", "Proserpine", "Bowen", "Collinsville",
    ],
  },
  {
    category: "Whitsunday Region",
    suburbs: [
      "Airlie Beach", "Cannonvale", "Jubilee Pocket", "Proserpine",
      "Bowen", "Collinsville", "Bowen", "Gumlu",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // TOWNSVILLE REGION & NORTH QLD
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Townsville — City",
    suburbs: [
      "Townsville", "West End", "North Ward", "Hyde Park", "Pimlico",
      "Belgian Gardens", "Mundingburra", "Hermit Park", "Garbutt",
      "Cranbrook", "Idalia", "Kirwan", "Thuringowa Central", "Annandale",
      "Kelso", "Bohle", "Cluden", "Condon", "Douglas", "Heatley",
      "Mysterton", "Oonoonba", "Aitkenvale", "Mount Louisa", "Rasmussen",
      "Bushland Beach", "Burdell", "Deeragun", "Jensen", "Bohle Plains",
      "Shaw", "Rosslea", "Currajong", "Willows", "Gulliver", "Heatley",
      "Wulguru",
    ],
  },
  {
    category: "North QLD — Regional",
    suburbs: [
      "Charters Towers", "Ingham", "Cardwell", "Tully", "Innisfail",
      "Mareeba", "Atherton", "Ravenshoe", "Dimbulah", "Mount Garnet",
      "Ayr", "Home Hill", "Bowen", "Cloncurry", "Julia Creek",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // CAIRNS REGION & FAR NORTH QLD
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Cairns — City",
    suburbs: [
      "Cairns City", "Parramatta Park", "Westcourt", "Edge Hill", "Manunda",
      "Mooroobool", "Woree", "Earlville", "White Rock", "Bentley Park",
      "Gordonvale", "Redlynch", "Smithfield", "Freshwater", "Brinsmead",
      "Bayview Heights", "Kanimbla", "Trinity Beach", "Palm Cove",
      "Clifton Beach", "Yorkeys Knob", "Kewarra Beach", "Holloways Beach",
      "Machans Beach", "Stratford", "Bungalow", "Aeroglen", "Manoora",
      "Portsmith", "Woree", "Edmonton",
    ],
  },
  {
    category: "Far North QLD",
    suburbs: [
      "Port Douglas", "Mossman", "Daintree", "Cooktown", "Weipa",
      "Bamaga", "Thursday Island", "Kuranda", "Mareeba", "Atherton",
      "Herberton", "Ravenshoe", "Mission Beach", "Innisfail", "Tully",
      "Cardwell", "Babinda",
    ],
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // OUTBACK & WESTERN QLD
  // ─────────────────────────────────────────────────────────────────────────────
  {
    category: "Outback & Western QLD",
    suburbs: [
      "Mount Isa", "Cloncurry", "Julia Creek", "Richmond", "Longreach",
      "Barcaldine", "Blackall", "Charleville", "Cunnamulla", "Quilpie",
      "Windorah", "Birdsville", "Bedourie", "Boulia", "Dajarra",
      "Camooweal", "Normanton", "Karumba", "Burketown", "Doomadgee",
      "Mornington Island", "Kowanyama", "Pormpuraaw",
    ],
  },
];
