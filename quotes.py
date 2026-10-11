"""A new nature / environment quote every day (rotates through the list by date)."""
import datetime as dt

QUOTES = [
    ("In every walk with nature one receives far more than he seeks.", "John Muir"),
    ("In nature nothing exists alone.", "Rachel Carson"),
    ("Heaven is under our feet as well as over our heads.", "Henry David Thoreau"),
    ("What is the use of a house if you haven't got a tolerable planet to put it on?", "Henry David Thoreau"),
    ("When we see land as a community to which we belong, we may begin to use it with love and respect.", "Aldo Leopold"),
    ("The earth provides enough to satisfy every man's needs, but not every man's greed.", "Attributed to Mahatma Gandhi"),
    ("What you do makes a difference, and you have to decide what kind of difference you want to make.", "Jane Goodall"),
    ("The greatest threat to our planet is the belief that someone else will save it.", "Robert Swan"),
    ("No one will protect what they don't care about, and no one will care about what they have never experienced.", "David Attenborough"),
    ("Ecology is permanent economy.", "Sunderlal Bahuguna, Chipko movement"),
    ("The Earth is what we all have in common.", "Wendell Berry"),
    ("When we plant trees, we plant the seeds of peace and seeds of hope.", "Wangari Maathai"),
    ("Nature does not hurry, yet everything is accomplished.", "Attributed to Lao Tzu"),
    ("The Earth is my mother, and I am her child.", "Atharva Veda (Prithvi Sukta)"),
    ("The world lives by the steady fall of rain; that is why rain is called nectar.", "Thirukkural 11 (paraphrased)"),
    ("We won't have a society if we destroy the environment.", "Margaret Mead"),
    ("The best time to plant a tree was twenty years ago. The second best time is now.", "Proverb"),
    ("Look deep into nature, and then you will understand everything better.", "Attributed to Albert Einstein"),
    ("Climb the mountains and get their good tidings. Nature's peace will flow into you as sunshine flows into trees.", "John Muir"),
    ("The clearest way into the Universe is through a forest wilderness.", "John Muir"),
    ("Conservation is a state of harmony between men and land.", "Aldo Leopold"),
    ("Water is the driving force of all nature.", "Attributed to Leonardo da Vinci"),
    ("Adopt the pace of nature: her secret is patience.", "Ralph Waldo Emerson"),
    ("Nature is not a place to visit. It is home.", "Gary Snyder"),
    ("The environment is where we all meet; where all have a mutual interest; it is the one thing all of us share.", "Lady Bird Johnson"),
    ("Think globally, act locally.", "Environmental movement slogan"),
    ("Earth and sky, woods and fields, lakes and rivers, the mountain and the sea, are excellent schoolmasters.", "John Lubbock"),
    ("Man is a part of nature, and his war against nature is inevitably a war against himself.", "Rachel Carson"),
    ("A nation that destroys its soils destroys itself.", "Franklin D. Roosevelt"),
    ("Water and air, the two essential fluids on which all life depends, have become global garbage cans.", "Jacques Cousteau"),
    ("The earth laughs in flowers.", "Ralph Waldo Emerson"),
]

def today(date=None):
    """Quote for a date (defaults to today in India, UTC+5:30). Same quote all day, a new one tomorrow."""
    d = date or (dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)).date()
    return QUOTES[d.toordinal() % len(QUOTES)]
