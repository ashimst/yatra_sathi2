export interface LocationOption {
  value: string;
  label: string;
  subtitle?: string;
  region: string;
  coords: [number, number];
  icon?: string;
}

export interface LocationGroup {
  groupName: string;
  options: LocationOption[];
}

export interface CorridorPreset {
  id: string;
  title: string;
  subtitle: string;
  origin: string;
  dest: string;
  days: number;
  pace: string;
  budget: string;
  badge: string;
  highlights: string[];
}

// Comprehensive Nepal Departure Hubs
export const DEPARTURE_HUB_GROUPS: LocationGroup[] = [
  {
    groupName: 'Major Central Air & Transit Hubs',
    options: [
      {
        value: 'Kathmandu',
        label: 'Kathmandu (Tribhuvan Intl & Ring Road)',
        subtitle: 'Capital Valley & Primary International Gateway',
        region: 'Bagmati',
        coords: [27.7172, 85.3240],
        icon: '🏛️'
      },
      {
        value: 'Pokhara',
        label: 'Pokhara (Domestic Airport & Prithvi Terminal)',
        subtitle: 'Annapurna & Western Himalayas Transit Base',
        region: 'Gandaki',
        coords: [28.2096, 83.9856],
        icon: '🏔️'
      },
      {
        value: 'Bharatpur',
        label: 'Bharatpur / Chitwan Hub',
        subtitle: 'Narayani River Basin & Southern Highway Hub',
        region: 'Bagmati / Narayani',
        coords: [27.6788, 84.4333],
        icon: '🦏'
      }
    ]
  },
  {
    groupName: 'High Mountain Airstrips',
    options: [
      {
        value: 'Lukla',
        label: 'Lukla (Tenzing-Hillary Airstrip)',
        subtitle: 'Gateway to Sagarmatha & Khumbu High Trails',
        region: 'Khumbu',
        coords: [27.6869, 86.7290],
        icon: '✈️'
      },
      {
        value: 'Jomsom',
        label: 'Jomsom High Mountain Airstrip',
        subtitle: 'Kali Gandaki Gorge & Lower Mustang Gateway',
        region: 'Mustang',
        coords: [28.7844, 83.7226],
        icon: '🌬️'
      }
    ]
  },
  {
    groupName: 'Southern & Regional Terminals',
    options: [
      {
        value: 'Bhairahawa',
        label: 'Bhairahawa (Gautam Buddha Intl Airport)',
        subtitle: 'Lumbini Sacred Lotus Garden Gateway',
        region: 'Lumbini',
        coords: [27.5028, 83.4500],
        icon: '🪷'
      },
      {
        value: 'Nepalgunj',
        label: 'Nepalgunj Western Border Hub',
        subtitle: 'Karnali & Far-Western Wilderness Transit',
        region: 'Banke',
        coords: [28.0500, 81.6167],
        icon: '🌿'
      },
      {
        value: 'Biratnagar',
        label: 'Biratnagar Eastern Airport Hub',
        subtitle: 'Eastern Tea Highlands & Kangchenjunga Transit',
        region: 'Koshi',
        coords: [26.4525, 87.2718],
        icon: '🍵'
      },
      {
        value: 'Janakpur',
        label: 'Janakpur Airport & Railway Terminal',
        subtitle: 'Historic Mithila Kingdom & Religious Hub',
        region: 'Madhesh',
        coords: [26.7288, 85.9244],
        icon: '🛕'
      },
      {
        value: 'Dhangadhi',
        label: 'Dhangadhi Far-West Terminal',
        subtitle: 'Suklaphanta & Mahakali Basin Gateway',
        region: 'Sudurpashchim',
        coords: [28.6833, 80.6000],
        icon: '🌾'
      }
    ]
  }
];

// Comprehensive Destination Corridors Across All of Nepal
export const DESTINATION_CORRIDOR_GROUPS: LocationGroup[] = [
  {
    groupName: 'Annapurna & Gandaki Sanctuary Corridors',
    options: [
      {
        value: 'Pokhara',
        label: 'Pokhara & Phewa Lakeside Tranquility',
        subtitle: 'Machhapuchhre views, caves, lakeside cafes',
        region: 'Gandaki',
        coords: [28.2096, 83.9856],
        icon: '⛵'
      },
      {
        value: 'Ghandruk',
        label: 'Ghandruk Gurung Cultural Village',
        subtitle: 'Stone-paved alleys, heritage museum, Annapurna South vista',
        region: 'Kaski',
        coords: [28.3756, 83.8073],
        icon: '🏡'
      },
      {
        value: 'Ghorepani',
        label: 'Ghorepani & Poon Hill Sunrise',
        subtitle: 'Scarlet rhododendron ridge & 360° Himalayan panorama',
        region: 'Myagdi',
        coords: [28.4005, 83.7020],
        icon: '🌅'
      },
      {
        value: 'Annapurna Base Camp',
        label: 'Annapurna Base Camp (ABC Sanctuary)',
        subtitle: 'Glacial amphitheater surrounded by 8,000m giants',
        region: 'Kaski / Annapurna',
        coords: [28.5300, 83.8780],
        icon: '🏔️'
      },
      {
        value: 'Bandipur',
        label: 'Bandipur Medieval Hilltop Bazaar',
        subtitle: 'Preserved 18th-century Newari architecture & ridge walks',
        region: 'Tanahun',
        coords: [27.9333, 84.4167],
        icon: '🏮'
      },
      {
        value: 'Gorkha',
        label: 'Gorkha Historic Durbar & Kalika Shrine',
        subtitle: 'Ancestral hilltop fortress of Nepal unification',
        region: 'Gorkha',
        coords: [28.0055, 84.6319],
        icon: '⚔️'
      },
      {
        value: 'Tansen',
        label: 'Tansen (Palpa) Hill Station & Rani Mahal',
        subtitle: 'Historic Dhaka weaving town overlooking Kali Gandaki',
        region: 'Palpa',
        coords: [27.8673, 83.5463],
        icon: '🏰'
      },
      {
        value: 'Manang',
        label: 'Manang High Valley & Tilicho Lake Base',
        subtitle: 'Tibetan plateau culture, yaks, and arid mountain desert',
        region: 'Manang',
        coords: [28.6667, 84.0167],
        icon: '❄️'
      }
    ]
  },
  {
    groupName: 'Kathmandu Valley & Sacred Heritage Corridors',
    options: [
      {
        value: 'Kathmandu',
        label: 'Kathmandu Valley Sacred Sanctuaries',
        subtitle: 'Pashupatinath, Boudhanath, Swayambhunath heritage',
        region: 'Kathmandu',
        coords: [27.7172, 85.3240],
        icon: '🛕'
      },
      {
        value: 'Patan',
        label: 'Patan Durbar & Newari Metal Artisan Square',
        subtitle: 'Golden Temple, fine arts, and medieval chowks',
        region: 'Lalitpur',
        coords: [27.6744, 85.3247],
        icon: '🎨'
      },
      {
        value: 'Bhaktapur',
        label: 'Bhaktapur City of Devotees & 55-Window Palace',
        subtitle: 'Ancient Newari pottery, Nyatapola temple, and ju-ju dhau',
        region: 'Bhaktapur',
        coords: [27.6710, 85.4298],
        icon: '🏺'
      },
      {
        value: 'Nagarkot',
        label: 'Nagarkot Himalayan Sunrise Ridge',
        subtitle: 'Sweeping panoramic views from Langtang to Everest',
        region: 'Bhaktapur / Kavre',
        coords: [27.7174, 85.5204],
        icon: '🌄'
      },
      {
        value: 'Dhulikhel',
        label: 'Dhulikhel & Namo Buddha Sacred Stupa',
        subtitle: 'Tigress compassion legend and Newari trade hill post',
        region: 'Kavrepalanchok',
        coords: [27.6186, 85.5531],
        icon: '☸️'
      },
      {
        value: 'Chandragiri',
        label: 'Chandragiri Cable Car & Bhaleshwor Mahadev',
        subtitle: 'Historic vantage ridge where King Prithvi surveyed the valley',
        region: 'Kathmandu Rim',
        coords: [27.6711, 85.2289],
        icon: '🚠'
      },
      {
        value: 'Balthali',
        label: 'Balthali Eco Foothills & Pine Valleys',
        subtitle: 'Untouched terraced village sanctuary with quiet homestays',
        region: 'Kavre',
        coords: [27.5500, 85.5333],
        icon: '🌲'
      }
    ]
  },
  {
    groupName: 'Trans-Himalayan & Mustang Realm',
    options: [
      {
        value: 'Lo Manthang',
        label: 'Lo Manthang (Walled Kingdom of Upper Mustang)',
        subtitle: 'Ancient Tibetan palaces, royal gompas, and sky caves',
        region: 'Upper Mustang',
        coords: [29.1825, 83.9567],
        icon: '👑'
      },
      {
        value: 'Muktinath',
        label: 'Muktinath Sacred Valley & 108 Spouts',
        subtitle: 'Holy salvation pilgrimage for Hindus and Buddhists',
        region: 'Mustang',
        coords: [28.8167, 83.8667],
        icon: '💧'
      },
      {
        value: 'Marpha',
        label: 'Marpha Apple Orchards & White Stone Alleys',
        subtitle: 'Famous Thakali stone masonry and mountain cider presses',
        region: 'Mustang',
        coords: [28.7523, 83.6845],
        icon: '🍏'
      },
      {
        value: 'Jomsom',
        label: 'Jomsom & Kali Gandaki Gorge',
        subtitle: 'World’s deepest gorge between Annapurna and Dhaulagiri',
        region: 'Mustang',
        coords: [28.7844, 83.7226],
        icon: '🏜️'
      }
    ]
  },
  {
    groupName: 'Everest & Khumbu High Sanctuary',
    options: [
      {
        value: 'Namche',
        label: 'Namche Bazaar (Sherpa Capital)',
        subtitle: 'Horseshoe amphitheater, Saturday market, acclimatization',
        region: 'Solukhumbu',
        coords: [27.8050, 86.7140],
        icon: '⛰️'
      },
      {
        value: 'Tengboche',
        label: 'Tengboche Sacred Monastery Ridge',
        subtitle: 'Mani Rimdu festival grounds under Ama Dablam’s peak',
        region: 'Solukhumbu',
        coords: [27.8358, 86.7644],
        icon: '📿'
      },
      {
        value: 'Everest Base Camp',
        label: 'Everest Base Camp & Kala Patthar (5,545m)',
        subtitle: 'Khumbu Icefall terminal and pinnacle Sagarmatha view',
        region: 'Solukhumbu',
        coords: [28.0026, 86.8528],
        icon: '🧗'
      }
    ]
  },
  {
    groupName: 'Langtang Valley & Alpine Lakes',
    options: [
      {
        value: 'Langtang',
        label: 'Langtang Valley & Kyanjin Gompa',
        subtitle: 'Valley of Glaciers, Swiss cheese factory, Kyanjin Ri climb',
        region: 'Rasuwa',
        coords: [28.2150, 85.5030],
        icon: '🧀'
      },
      {
        value: 'Gosainkunda',
        label: 'Gosainkunda Sacred Alpine Lakes (4,380m)',
        subtitle: 'Shiva’s trident-carved holy blue tarns in pristine mist',
        region: 'Rasuwa',
        coords: [28.0833, 85.4167],
        icon: '🌊'
      },
      {
        value: 'Helambu',
        label: 'Helambu Apple & Sherpa Trail',
        subtitle: 'Gentle monastery ridges and rhododendron woodlands',
        region: 'Sindhupalchok',
        coords: [28.0333, 85.5500],
        icon: '🍎'
      },
      {
        value: 'Kalinchowk',
        label: 'Kalinchowk Bhagwati Shrine & Kuri Village',
        subtitle: 'High winter snow crest and holy goddess sanctuary',
        region: 'Dolakha',
        coords: [27.7478, 86.0267],
        icon: '❄️'
      }
    ]
  },
  {
    groupName: 'Terai Wildlife & Pilgrimage Sanctuaries',
    options: [
      {
        value: 'Chitwan',
        label: 'Chitwan National Park & Sauraha Safari',
        subtitle: 'One-horned rhinos, Royal Bengal tigers, canoe expeditions',
        region: 'Chitwan',
        coords: [27.5341, 84.4525],
        icon: '🐅'
      },
      {
        value: 'Lumbini',
        label: 'Lumbini Sacred Lotus Garden & Mayadevi Temple',
        subtitle: 'Birthplace of Siddhartha Gautama with global peace pagodas',
        region: 'Rupandehi',
        coords: [27.4842, 83.2759],
        icon: '🪷'
      },
      {
        value: 'Janakpur',
        label: 'Janakpur Janaki Mandir & Mithila Culture',
        subtitle: 'Magnificent Mughal-Rajput marble palace temple',
        region: 'Dhanusha',
        coords: [26.7288, 85.9244],
        icon: '👑'
      },
      {
        value: 'Bardia',
        label: 'Bardia National Park Wilderness',
        subtitle: 'Pristine Karnali river plains & wild elephant territory',
        region: 'Bardiya',
        coords: [28.5833, 81.3333],
        icon: '🐘'
      }
    ]
  },
  {
    groupName: 'Wild West & Alpine High Lakes (Trans-Karnali)',
    options: [
      {
        value: 'Rara',
        label: 'Rara Lake (Queen of Himalayan Waters, 2,990m)',
        subtitle: 'Mirror-clear turquoise waters encircled by blue pine forests',
        region: 'Mugu',
        coords: [29.5375, 82.0833],
        icon: '💎'
      },
      {
        value: 'Shey Phoksundo',
        label: 'Shey Phoksundo Lake & Ringmo Bon Gompa',
        subtitle: 'Deep aquamarine jewel of Dolpa with 800-year-old Bon shrines',
        region: 'Dolpa',
        coords: [29.2100, 82.9500],
        icon: '🧿'
      },
      {
        value: 'Khaptad',
        label: 'Khaptad National Park & Meditation Moors',
        subtitle: 'Rolling sub-alpine meadows, medicinal herbs, sacred ashram',
        region: 'Bajhang / Doti',
        coords: [29.3667, 81.1667],
        icon: '🧘'
      }
    ]
  },
  {
    groupName: 'Eastern Tea Highlands & Kangchenjunga',
    options: [
      {
        value: 'Ilam',
        label: 'Ilam & Kanyam Tea Highland Gardens',
        subtitle: 'Rolling emerald tea hills, fog cascades, and organic chiyā',
        region: 'Ilam',
        coords: [26.9089, 87.9263],
        icon: '🌱'
      },
      {
        value: 'Dharan',
        label: 'Dharan & Bhedetar Cloud Point',
        subtitle: 'Foothill culture, Charles Point vista, and Baraha Kshetra',
        region: 'Sunsari',
        coords: [26.8124, 87.2835],
        icon: '☁️'
      }
    ]
  }
];

// Universal Flattened Coordinates Map
export const NEPAL_LOCATIONS_MAP: Record<string, [number, number]> = {
  Kathmandu: [27.7172, 85.3240],
  Pokhara: [28.2096, 83.9856],
  Chitwan: [27.5341, 84.4525],
  Bharatpur: [27.6788, 84.4333],
  Sauraha: [27.5816, 84.4947],
  Bandipur: [27.9333, 84.4167],
  Nagarkot: [27.7174, 85.5204],
  Dhulikhel: [27.6186, 85.5531],
  Lumbini: [27.4842, 83.2759],
  Janakpur: [26.7288, 85.9244],
  Mustang: [28.7844, 83.7226],
  Jomsom: [28.7844, 83.7226],
  Muktinath: [28.8167, 83.8667],
  'Lo Manthang': [29.1825, 83.9567],
  Marpha: [28.7523, 83.6845],
  Ghandruk: [28.3756, 83.8073],
  Ghorepani: [28.4005, 83.7020],
  'Annapurna Base Camp': [28.5300, 83.8780],
  ABC: [28.5300, 83.8780],
  Namche: [27.8050, 86.7140],
  Lukla: [27.6869, 86.7290],
  Tengboche: [27.8358, 86.7644],
  'Everest Base Camp': [28.0026, 86.8528],
  EBC: [28.0026, 86.8528],
  Langtang: [28.2150, 85.5030],
  'Kyanjin Gompa': [28.2133, 85.5678],
  Gosainkunda: [28.0833, 85.4167],
  Helambu: [28.0333, 85.5500],
  Kalinchowk: [27.7478, 86.0267],
  Rara: [29.5375, 82.0833],
  'Shey Phoksundo': [29.2100, 82.9500],
  Ilam: [26.9089, 87.9263],
  Kanyam: [26.8500, 88.0500],
  Tansen: [27.8673, 83.5463],
  Palpa: [27.8673, 83.5463],
  Gorkha: [28.0055, 84.6319],
  Dharan: [26.8124, 87.2835],
  Biratnagar: [26.4525, 87.2718],
  Nepalgunj: [28.0500, 81.6167],
  Bhairahawa: [27.5028, 83.4500],
  Bardia: [28.5833, 81.3333],
  Dhangadhi: [28.6833, 80.6000],
  Manang: [28.6667, 84.0167],
  Bhaktapur: [27.6710, 85.4298],
  Patan: [27.6744, 85.3247],
  Chandragiri: [27.6711, 85.2289],
  Balthali: [27.5500, 85.5333],
  Khaptad: [29.3667, 81.1667]
};

// Curated Expedition Presets for Instant 1-Click Launch
export const CURATED_CORRIDOR_PRESETS: CorridorPreset[] = [
  {
    id: 'ktm-pkr-classic',
    title: 'Valley-to-Lake Sanctuary Classic',
    subtitle: 'Kathmandu to Pokhara via Prithvi Gorge & Trisuli River',
    origin: 'Kathmandu',
    dest: 'Pokhara',
    days: 3,
    pace: 'Balanced',
    budget: 'Medium',
    badge: 'Most Popular',
    highlights: ['Trisuli River Gorge', 'Bandipur Hilltop Post', 'Phewa Lake & Peace Pagoda']
  },
  {
    id: 'pkr-ghandruk-poonhill',
    title: 'Annapurna Balcony & Poon Hill',
    subtitle: 'Pokhara to Ghandruk & Ghorepani Rhododendron Crest',
    origin: 'Pokhara',
    dest: 'Ghandruk',
    days: 4,
    pace: 'Balanced',
    budget: 'Medium',
    badge: 'Trekker Classic',
    highlights: ['Ghandruk Heritage Museum', 'Annapurna South Sunrise', 'Traditional Gurung Homestay']
  },
  {
    id: 'jomsom-mustang',
    title: 'Trans-Himalayan Walled Kingdom',
    subtitle: 'Jomsom to Lo Manthang & Muktinath Sacred Springs',
    origin: 'Jomsom',
    dest: 'Lo Manthang',
    days: 5,
    pace: 'Relaxed',
    budget: 'Medium',
    badge: 'Ancient Beyul',
    highlights: ['Muktinath 108 Sacred Spouts', 'Red Cliffs of Dhakmar', 'Lo Manthang King’s Palace']
  },
  {
    id: 'ktm-langtang',
    title: 'Langtang Valley & High Glacial Tarns',
    subtitle: 'Kathmandu to Kyanjin Gompa & Gosainkunda Basin',
    origin: 'Kathmandu',
    dest: 'Langtang',
    days: 5,
    pace: 'Balanced',
    budget: 'Medium',
    badge: 'Alpine Wilderness',
    highlights: ['Kyanjin Ri Glacial Panoramic', 'Yak Cheese Craft Co-Op', 'Langtang Tamang Heritage']
  },
  {
    id: 'ktm-chitwan-safari',
    title: 'Royal Subtropical Wilderness',
    subtitle: 'Kathmandu to Chitwan National Park & Sauraha',
    origin: 'Kathmandu',
    dest: 'Chitwan',
    days: 3,
    pace: 'Relaxed',
    budget: 'Medium',
    badge: 'Wildlife Sanctuary',
    highlights: ['One-Horned Rhino Canoe Patrol', 'Tharu Stick Dance & Culture', 'Elephant Breeding Center']
  },
  {
    id: 'ktm-rara-alpine',
    title: 'Wild West Queen of Alpine Lakes',
    subtitle: 'Nepalgunj to Rara Lake (2,990m) Deep Wilderness',
    origin: 'Nepalgunj',
    dest: 'Rara',
    days: 6,
    pace: 'Balanced',
    budget: 'Medium',
    badge: 'Untamed Frontier',
    highlights: ['Murma Top Vista', 'Sinja Valley Ancient Ruins', 'Pristine Blue Pine Shores']
  }
];

