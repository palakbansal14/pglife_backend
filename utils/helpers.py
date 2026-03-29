from bson import ObjectId
from datetime import datetime
import random, string


def serialize(doc):
    """Recursively convert MongoDB doc to JSON-serializable dict."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            if k == "_id":
                result["_id"] = str(v)
            elif isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                result[k] = serialize(v)
            else:
                result[k] = v
        return result
    return doc


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def paginate(query_cursor, page, limit):
    """Apply skip/limit to a pymongo cursor."""
    skip = (page - 1) * limit
    return query_cursor.skip(skip).limit(limit)
