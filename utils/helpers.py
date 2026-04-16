from bson import ObjectId
from datetime import datetime
import random, string


def _to_camel(name: str) -> str:
    """Convert snake_case key to camelCase (e.g. monthly_rent → monthlyRent)."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def serialize(doc):
    """Recursively convert MongoDB doc to JSON-serializable dict with camelCase keys."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            # _id stays as _id, all other keys go camelCase
            camel_k = "_id" if k == "_id" else _to_camel(k)
            if k == "_id":
                result["_id"] = str(v)
            elif isinstance(v, ObjectId):
                result[camel_k] = str(v)
            elif isinstance(v, datetime):
                result[camel_k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                result[camel_k] = serialize(v)
            else:
                result[camel_k] = v
        return result
    return doc


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def paginate(query_cursor, page, limit):
    """Apply skip/limit to a pymongo cursor."""
    skip = (page - 1) * limit
    return query_cursor.skip(skip).limit(limit)
