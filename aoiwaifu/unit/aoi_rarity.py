rarity_map = {
    1: "Frequent 🫧",
    2: "Superior 🎋",
    3: "Elite 🪸",
    4: "Majestic 👑",
    5: "Mythical 🧜‍♀️",
    6: "Angelic 🪄",
    7: "Galactic 🌌",
    8: "Phantom 🧌",
    9: "Pookie 🐣",
    10: "Exclusive 🪎",
    11: "Habitual 👘",
    12: "Winter ☃️",
    13: "Valentine's 💕",
    14: "Summer 🏜️",
    15: "Chibi 🎀",
    16: "Cosplay 🗿",
    17: "Rainy 🌧️",
    18: "Seasonal 🍁",
    19: "DIY 🎨",
    20: "Imaginative 🍀",
    21: "Diwali 🪔",
    22: "Censored 💋",
}

# Names and emoji lookup are derived from the single canonical map.
RARITY_NAMES = list(rarity_map.values())
rarity_map2 = {
    name: name.rsplit(" ", 1)[-1]
    for name in RARITY_NAMES
}
