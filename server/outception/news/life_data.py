"""Lifestyle & interest news feeds — travel, food, culture, hobbies, and every
other aspect of life — as Google News search feeds.

Each entry becomes a feed (getters in ``sources/life.py``, ``SOURCES`` rows in
``metadata.py``) under a topic column. Plain data only, so both modules can
import it without a circular dependency.
"""

from __future__ import annotations

import re

# (google-news-query, source_id, card_name, kicker, column)
LifeFeed = tuple[str, str, str, str, str]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _q(text: str) -> str:
    return re.sub(r"\s+", "+", text.strip())


# (column, kicker, query_suffix, [topic names]). The query is "topic+suffix";
# the id is "life-{slug(topic)}"; the card title is the topic.
_GROUPS: list[tuple[str, str, str, list[str]]] = [
    (
        "travel",
        "Travel",
        "travel",
        [
            "Budget Travel",
            "Luxury Travel",
            "Solo Travel",
            "Backpacking",
            "Cruises",
            "National Parks",
            "Road Trips",
            "Flight Deals",
            "Hotels",
            "Digital Nomad",
            "Adventure Travel",
            "Beach Destinations",
            "City Breaks",
            "Ski Holidays",
            "Safari",
            "Japan Travel",
            "Europe Travel",
            "Southeast Asia Travel",
            "Caribbean Travel",
            "Travel Photography",
            "Camping",
            "Hiking",
            "Van Life",
            "Theme Parks",
            "Airlines",
            "Travel Deals",
        ],
    ),
    (
        "food",
        "Food",
        "",
        [
            "Recipes",
            "Healthy Recipes",
            "Baking",
            "Vegan Recipes",
            "Vegetarian Recipes",
            "Keto Diet",
            "BBQ Grilling",
            "Street Food",
            "Fine Dining",
            "Restaurant News",
            "Wine",
            "Craft Beer",
            "Cocktails",
            "Coffee",
            "Meal Prep",
            "Air Fryer Recipes",
            "Desserts",
            "Italian Food",
            "Mexican Food",
            "Indian Food",
            "Asian Cuisine",
            "Michelin Stars",
            "Food Trucks",
            "Whiskey",
            "Vegan Food",
            "Sourdough Bread",
            "Pizza",
        ],
    ),
    (
        "lifestyle",
        "Lifestyle",
        "",
        [
            "Fashion",
            "Men's Fashion",
            "Streetwear",
            "Sneakers",
            "Beauty",
            "Skincare",
            "Makeup",
            "Haircare",
            "Fitness",
            "Yoga",
            "Home Workout",
            "Weight Loss",
            "Mental Health",
            "Mindfulness",
            "Meditation",
            "Sleep Science",
            "Productivity",
            "Minimalism",
            "Parenting",
            "Pregnancy",
            "Weddings",
            "Dating",
            "Relationships",
            "Interior Design",
            "Home Decor",
            "DIY Projects",
            "Gardening",
            "Houseplants",
            "Pets",
            "Dogs",
            "Cats",
            "Self Improvement",
            "Luxury Lifestyle",
            "Watches",
            "Jewelry",
            "Wellness",
            "Nutrition",
        ],
    ),
    (
        "culture",
        "Culture",
        "",
        [
            "Books",
            "Book Reviews",
            "Bestsellers",
            "Poetry",
            "Art",
            "Museums",
            "Photography",
            "History",
            "Ancient History",
            "Architecture",
            "Comedy",
            "Stand-up Comedy",
            "Memes",
            "Celebrity News",
            "Royal Family",
            "Astrology",
            "Philosophy",
            "Theatre",
            "Broadway",
            "Anime",
            "Manga",
            "Comics",
            "K-pop",
            "Pop Culture",
            "Fan Culture",
            "Cosplay",
        ],
    ),
    (
        "science",
        "Science",
        "",
        [
            "Space",
            "NASA",
            "Astronomy",
            "Physics",
            "Biology",
            "Psychology",
            "Neuroscience",
            "Nature",
            "Wildlife",
            "Ocean Science",
            "Archaeology",
            "Genetics",
            "Robotics",
            "Mars",
            "Black Holes",
            "Dinosaurs",
            "Volcanoes",
            "Renewable Energy",
        ],
    ),
    (
        "tech",
        "Tech",
        "",
        [
            "Cars",
            "Electric Cars",
            "Motorcycles",
            "Gadgets",
            "Smartphones",
            "Smart Home",
            "Drones",
            "PC Building",
            "Photography Gear",
            "Headphones",
            "Apple",
            "Android",
            "Cameras",
            "Virtual Reality",
        ],
    ),
    (
        "entertainment",
        "Entertainment",
        "",
        [
            "Movies",
            "Netflix",
            "Streaming",
            "TV Shows",
            "Box Office",
            "Music",
            "Hip Hop",
            "Rock Music",
            "Pop Music",
            "Country Music",
            "EDM",
            "Concerts",
            "Podcasts",
            "Video Games",
            "Nintendo",
            "PlayStation",
            "Xbox",
            "Board Games",
            "Reality TV",
            "Documentaries",
        ],
    ),
    (
        "finance",
        "Finance",
        "",
        [
            "Personal Finance",
            "Investing",
            "Real Estate",
            "Mortgages",
            "Retirement",
            "Side Hustles",
            "Passive Income",
            "Frugal Living",
            "Credit Cards",
            "Careers",
            "Remote Work",
            "Entrepreneurship",
            "Small Business",
            "Budgeting",
            "Index Funds",
        ],
    ),
    (
        "social",
        "Social",
        "",
        [
            "Life Hacks",
            "Life Advice",
            "Motivation",
            "Success Stories",
            "Good Habits",
            "Viral Trends",
        ],
    ),
]


def _build() -> list[LifeFeed]:
    feeds: list[LifeFeed] = []
    seen: set[str] = set()
    for column, kicker, suffix, topics in _GROUPS:
        for topic in topics:
            source_id = f"life-{_slug(topic)}"
            if source_id in seen:
                continue
            seen.add(source_id)
            query = _q(f"{topic} {suffix}") if suffix else _q(topic)
            feeds.append((query, source_id, topic, kicker, column))
    return feeds


LIFE_FEEDS: list[LifeFeed] = _build()
