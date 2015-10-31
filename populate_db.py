"""Populate the database for testing"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import init_db, Base, db_session as session
from models import  User, Category, Item

init_db()

# Create users
darth_vader = User(name="Darth Vader", email="darth.vader@galempire.com")
emperor_palpatine = User(
    name="Emperor Palpatine", email="emperor.palpatine@galempire.com")
revan = User(name="Revan", email="revan@oldempire.com")

session.add_all([darth_vader, emperor_palpatine, revan])
session.commit()

# Create categories
# Reference: http://starwars.wikia.com/
starfighter = Category(name="Starfighter", description="Small one- or "
                       "two-man vessels typically used for dogfighting.")
capital_ship = Category(name="Capital Ship", description="Largest of "
                        "starships, often used as a warship.")
scout_vessel = Category(name="Scout Vessel", description="Small, fast "
                        "ships used to scout an area before a main "
                        "force arrives.")
blaster_pistol = Category(name="Blaster Pistol", description="Small "
                          "handheld blasters.")
blaster_rifle = Category(name="Blaster Rifle", description="Heavy duty "
                         "blaster variants, much more powerful than pistols.")
blaster_cannon = Category(name="Blaster Cannon", description="Limited-range "
                          "heavy artillery variants of the handheld blasters.")
lightsaber = Category(name="Lightsaber", description="Plasma blade weapons "
                      "with a single blade.")
double_bladed_lightsaber = Category(name="Double-bladed Lightsaber",
                                    description="Plasma blade weapons with a "
                                    "blades extending from both sides of a "
                                    "single hilt.")

session.add_all([starfighter, capital_ship, scout_vessel,
                 blaster_pistol, blaster_rifle, blaster_cannon,
                 lightsaber, double_bladed_lightsaber])
session.commit()

tie_fighter = Item(name="TIE Fighter", category_id=1, user_id=1,
                   description="Small in size and manufactured en masse, "
                   "the TIE Fighter is the signature starfighter of the "
                   "Galactic Empire favored for their versatility.",
                   image="TIEfighter2-Fathead.png")

session.add(tie_fighter)
session.commit()
