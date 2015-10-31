""" Setup the the models for the catalog db."""
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine



"""Define the User Model for the database"""


class User(Base):

    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=datetime.datetime.now)
    modified = Column(DateTime, onupdate=datetime.datetime.now)
    name = Column(String(100), nullable=True)
    email = Column(String(250))
    image = Column(String(250), nullable=True)
    items = relationship("Item", backref="user")


    """Return Category object data in easily serializeable format"""
    @property
    def serialize(self):

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image': self.image
        }


"""Define the Category Model for the database"""


class Category(Base):

    __tablename__ = "category"

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=datetime.datetime.now)
    modified = Column(DateTime, onupdate=datetime.datetime.now)
    name = Column(String(100))
    description = Column(Text, nullable=True)
    image = Column(String(250), nullable=True)
    items = relationship("Item", backref="category")

    """Return Category object data in easily serializeable format"""
    @property
    def serialize(self):

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image': self.image
        }


"""Define the Item Model for the database"""


class Item(Base):

    __tablename__ = "item"

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=datetime.datetime.now)
    modified = Column(DateTime, onupdate=datetime.datetime.now)
    name = Column(String(100))
    description = Column(Text)
    image = Column(String(250), nullable=True)
    category_id = Column(Integer, ForeignKey('category.id'))
    user_id = Column(Integer, ForeignKey('user.id'))



    """Return Item object data in easily serializeable format"""
    @property
    def serialize(self):

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'category_id': self.category_id,
            'user_id': self.user_id
        }

