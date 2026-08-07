from typing import List

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.database import Base


class Country(Base):
    __tablename__ = "country"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    companies: Mapped[List["Company"]] = relationship(back_populates="country_name")


class Company(Base):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, unique=True
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    country: Mapped[int] = mapped_column(ForeignKey("country.id"))
    country_name: Mapped["Country"] = relationship(back_populates="companies")
    iata: Mapped[str] = mapped_column(String, unique=True)
    icao: Mapped[str] = mapped_column(String, unique=True)


class PlaneTable(Base):
    __tablename__ = "plane"
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, unique=True
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    companies: Mapped[str] = mapped_column(String, unique=True)
    seats: Mapped[str] = mapped_column(Integer, unique=True)


class TravelPurposes(Base):
    __tablename__ = "travel_purposes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    purpose: Mapped[str] = mapped_column(String, unique=True)
