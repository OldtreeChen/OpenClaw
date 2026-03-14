export const restaurants = [
  {
    id: "taipei-umami-grill",
    name: "Umami Grill",
    city: "Taipei",
    area: "Xinyi",
    cuisine: "Japanese BBQ",
    priceLevel: "$$$",
    rating: 4.7,
    tags: ["wagyu", "date-night", "private-room"],
    address: "No. 88, Songren Rd., Xinyi District, Taipei",
    reservationChannels: ["phone", "inline"],
    phone: "+886-2-2700-1122",
    reservationUrl: "https://example.com/umami-grill",
    availability: {
      "2026-03-14": ["18:00", "19:30", "20:00"],
      "2026-03-15": ["12:00", "18:30", "20:30"]
    }
  },
  {
    id: "taipei-sea-salt",
    name: "Sea Salt Table",
    city: "Taipei",
    area: "Da'an",
    cuisine: "Seafood",
    priceLevel: "$$$",
    rating: 4.6,
    tags: ["business", "wine", "fresh-fish"],
    address: "No. 216, Section 4, Zhongxiao E. Rd., Da'an District, Taipei",
    reservationChannels: ["phone", "opentable"],
    phone: "+886-2-2755-8811",
    reservationUrl: "https://example.com/sea-salt-table",
    availability: {
      "2026-03-14": ["17:30", "19:00"],
      "2026-03-15": ["18:00", "19:30", "21:00"]
    }
  },
  {
    id: "taipei-noodle-lab",
    name: "Noodle Lab",
    city: "Taipei",
    area: "Zhongshan",
    cuisine: "Modern Taiwanese",
    priceLevel: "$$",
    rating: 4.5,
    tags: ["casual", "family", "signature-noodles"],
    address: "No. 12, Lane 40, Nanjing W. Rd., Zhongshan District, Taipei",
    reservationChannels: ["phone"],
    phone: "+886-2-2522-9911",
    reservationUrl: "",
    availability: {
      "2026-03-14": ["11:30", "13:00", "18:00"],
      "2026-03-15": ["11:30", "12:00", "18:30", "19:00"]
    }
  },
  {
    id: "taichung-firewood",
    name: "Firewood Bistro",
    city: "Taichung",
    area: "Xitun",
    cuisine: "Steakhouse",
    priceLevel: "$$$",
    rating: 4.8,
    tags: ["steak", "anniversary", "cocktails"],
    address: "No. 31, Chaofu Rd., Xitun District, Taichung",
    reservationChannels: ["inline", "phone"],
    phone: "+886-4-2258-7070",
    reservationUrl: "https://example.com/firewood-bistro",
    availability: {
      "2026-03-14": ["18:00", "20:00"],
      "2026-03-15": ["18:30", "19:00", "20:30"]
    }
  }
];
