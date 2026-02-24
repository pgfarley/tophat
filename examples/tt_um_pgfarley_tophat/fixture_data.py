# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

# Features are encoded as 8-bit values (these fixtures currently use 0-63).
# Output is opening-weekend revenue in $M.
FEATURES = [
    "budget_10m",
    "marketing_5m",
    "franchise_strength",
    "star_power",
    "critic_buzz",
    "family_friendliness",
    "release_timing",
    "screen_count_100",
]

EXAMPLES = [
    {
        "name": "Indie Mystery",
        "features": {
            "budget_10m": 4,
            "marketing_5m": 6,
            "franchise_strength": 10,
            "star_power": 12,
            "critic_buzz": 15,
            "family_friendliness": 20,
            "release_timing": 10,
            "screen_count_100": 18,
        },
        "expected": 8,
    },
    {
        "name": "Festival Darling",
        "features": {
            "budget_10m": 4,
            "marketing_5m": 6,
            "franchise_strength": 10,
            "star_power": 12,
            "critic_buzz": 30,
            "family_friendliness": 20,
            "release_timing": 10,
            "screen_count_100": 18,
        },
        "expected": 18,
    },
    {
        "name": "Mid-Budget Original",
        "features": {
            "budget_10m": 12,
            "marketing_5m": 10,
            "franchise_strength": 10,
            "star_power": 18,
            "critic_buzz": 18,
            "family_friendliness": 30,
            "release_timing": 22,
            "screen_count_100": 20,
        },
        "expected": 25,
    },
    {
        "name": "Wide Release Original",
        "features": {
            "budget_10m": 12,
            "marketing_5m": 28,
            "franchise_strength": 10,
            "star_power": 22,
            "critic_buzz": 18,
            "family_friendliness": 30,
            "release_timing": 22,
            "screen_count_100": 20,
        },
        "expected": 45,
    },
    {
        "name": "Modest Sequel (Off-Peak)",
        "features": {
            "budget_10m": 18,
            "marketing_5m": 18,
            "franchise_strength": 40,
            "star_power": 22,
            "critic_buzz": 18,
            "family_friendliness": 25,
            "release_timing": 30,
            "screen_count_100": 30,
        },
        "expected": 55,
    },
    {
        "name": "Summer Sequel",
        "features": {
            "budget_10m": 18,
            "marketing_5m": 22,
            "franchise_strength": 40,
            "star_power": 22,
            "critic_buzz": 18,
            "family_friendliness": 25,
            "release_timing": 50,
            "screen_count_100": 30,
        },
        "expected": 85,
    },
    {
        "name": "Big Franchise (Modest Stars)",
        "features": {
            "budget_10m": 20,
            "marketing_5m": 26,
            "franchise_strength": 40,
            "star_power": 20,
            "critic_buzz": 20,
            "family_friendliness": 25,
            "release_timing": 50,
            "screen_count_100": 45,
        },
        "expected": 95,
    },
    {
        "name": "Mega Franchise Event",
        "features": {
            "budget_10m": 24,
            "marketing_5m": 30,
            "franchise_strength": 55,
            "star_power": 40,
            "critic_buzz": 30,
            "family_friendliness": 25,
            "release_timing": 55,
            "screen_count_100": 50,
        },
        "expected": 140,
    },
]


def vectorize_u8(feature_map):
    return [int(feature_map[name]) & 0xFF for name in FEATURES]
