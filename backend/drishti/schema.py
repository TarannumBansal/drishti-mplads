"""Canonical Drishti work schema. Source columns are mapped onto these.
Fields are OPTIONAL unless marked required; missing fields are never fabricated."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Field:
    name: str
    required: bool
    kind: str          # id | text | category | number | money | date | float
    aliases: tuple     # common source header variants (lowercased, for auto-mapping)

CANONICAL = [
    Field("work_id", True, "id", ("work id","workid","work_code","id","work no","work number","sr no")),
    Field("title", False, "text", ("title","work name","name of work","scheme")),
    Field("description", False, "text", ("description","work description","details","nature of work")),
    Field("work_type", False, "category", ("work type","work category","category","type of work","sector")),
    Field("district", False, "category", ("district","district name")),
    Field("state", False, "category", ("state","state/ut","state name")),
    Field("constituency", False, "category", ("constituency","lok sabha","rajya sabha","ls constituency")),
    Field("mp", False, "category", ("mp","member","mp name","name of mp")),
    Field("year", False, "number", ("year","financial year","fin year","fy","sanction year")),
    Field("size", False, "float", ("size","length","area","dimension")),
    Field("quantity", False, "float", ("quantity","qty","units","no of units")),
    Field("unit", False, "text", ("unit","uom","measure")),
    Field("sanctioned_amount", True, "money", ("sanctioned amount","amount sanctioned","cost","estimated cost","sanctioned amount (in rs.)","sanctioned cost","amount")),
    Field("expenditure", False, "money", ("expenditure","amount spent","expenditure incurred","utilised","utilized amount")),
    Field("fund_release", False, "money", ("fund release","released amount","funds released","amount released")),
    Field("implementing_agency", False, "category", ("implementing agency","agency","executing agency","ia")),
    Field("sanction_date", False, "date", ("sanction date","recommendation date","date of sanction","recommended date","sanctioned on")),
    Field("start_date", False, "date", ("start date","work start date","commencement date")),
    Field("expected_completion_date", False, "date", ("expected completion","target date","scheduled completion")),
    Field("actual_completion_date", False, "date", ("completion date","actual completion","date of completion")),
    Field("status", False, "category", ("status","work status","current status","stage")),
    Field("latitude", False, "float", ("latitude","lat")),
    Field("longitude", False, "float", ("longitude","lon","lng","long")),
    Field("source_record_id", False, "id", ("source id","record id","reference id")),
]
REQUIRED = [f.name for f in CANONICAL if f.required]
BY_NAME = {f.name: f for f in CANONICAL}
