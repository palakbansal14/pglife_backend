from flask import request, jsonify
import re


def chat_message():
    data = request.get_json()
    message = data.get("message", "").strip()
    lower = message.lower()

    response = {"type": "text", "content": ""}
    filters = {}

    # ── City detection ─────────────────────────────────
    city_map = {"noida": "Noida", "delhi": "Delhi", "gurgaon": "Gurgaon", "bangalore": "Bangalore"}
    for key, val in city_map.items():
        if key in lower:
            filters["city"] = val
            break

    # ── Gender detection ────────────────────────────────
    if any(w in lower for w in ["girls", "female", "ladies", "girl"]):
        filters["gender"] = "Girls"
    elif any(w in lower for w in ["boys", "male", "gents", "men", "boy"]):
        filters["gender"] = "Boys"
    elif any(w in lower for w in ["coliving", "co-living", "coed"]):
        filters["gender"] = "Coliving"

    # ── Budget detection ────────────────────────────────
    budget_match = re.search(
        r"(?:under|below|upto|max|within)\s*(?:rs\.?|₹)?\s*([\d,]+)|"
        r"([\d,]+)\s*(?:rs|rupees|₹|per month|\/month|\/mo)",
        lower
    )
    if budget_match:
        raw = (budget_match.group(1) or budget_match.group(2) or "").replace(",", "")
        try:
            val = int(raw)
            if 500 < val < 100000:
                filters["maxBudget"] = val
        except ValueError:
            pass

    # ── Greeting ────────────────────────────────────────
    if re.match(r"^(hi|hello|hey|namaste|hii|helo|sup)\b", lower):
        response["content"] = (
            "Namaste! 👋 I'm PG Life Assistant.\n\n"
            "Tell me your city, budget & preference and I'll find the best PG for you!\n\n"
            "Example: *Girls PG in Noida under ₹10,000*"
        )
        return jsonify({"success": True, "response": response}), 200

    # ── If filters found → redirect ─────────────────────
    if filters:
        from urllib.parse import urlencode
        query_string = urlencode(filters)
        city_text = filters.get("city", "all cities")
        gender_text = filters.get("gender", "")
        budget_text = f"under ₹{filters['maxBudget']:,}" if "maxBudget" in filters else ""

        response = {
            "type": "redirect",
            "content": (
                f"Great! Found PG options for you 🏠\n"
                f"Searching {city_text}{' · ' + gender_text if gender_text else ''}{' · ' + budget_text if budget_text else ''}"
            ),
            "url": f"/listings?{query_string}",
            "filters": filters,
        }

    # ── Static FAQ replies ──────────────────────────────
    elif any(w in lower for w in ["price", "cost", "rent", "budget", "kitna"]):
        response["content"] = (
            "PG prices vary by city 💰\n\n"
            "• Noida: ₹5,000 – ₹20,000/month\n"
            "• Delhi: ₹6,000 – ₹25,000/month\n"
            "• Gurgaon: ₹7,000 – ₹30,000/month\n"
            "• Bangalore: ₹6,000 – ₹25,000/month\n\n"
            "Tell me your city & budget for exact results!"
        )
    elif any(w in lower for w in ["food", "meal", "khana", "tiffin"]):
        response["content"] = (
            "Many PGs on PG Life include food! 🍱\n"
            "Use the **Food** filter when searching. "
            "Typically adds ₹2,000–₹5,000 to monthly cost."
        )
    elif any(w in lower for w in ["contact", "owner", "phone", "number"]):
        response["content"] = (
            "To contact an owner 📞:\n"
            "1. Open any PG listing\n"
            "2. Click **Show Contact Number**\n"
            "3. Login if prompted — then the number is revealed!"
        )
    elif any(w in lower for w in ["list", "add", "register", "property", "apna pg"]):
        response["content"] = (
            "Want to list your PG? 🏢\n"
            "It's completely free!\n"
            "1. Click **Login** → Register as Owner\n"
            "2. Go to **Dashboard → Add New PG**\n"
            "3. Upload photos & details — Go Live! 🚀"
        )
    elif any(w in lower for w in ["wifi", "ac", "amenities", "facilities"]):
        response["content"] = (
            "You can filter PGs by amenities! 🔍\n"
            "Available filters: WiFi, AC, Food, Laundry, Parking, Gym, CCTV, Hot Water\n\n"
            "Use the **More Filters** option on the listings page."
        )
    else:
        response["content"] = (
            "I can help you find PGs! 🏠 Try:\n\n"
            "• *Girls PG in Noida under 10000*\n"
            "• *Boys PG Gurgaon with food*\n"
            "• *Coliving in Bangalore*\n\n"
            "Or ask me about prices, amenities, or how to list your PG."
        )

    return jsonify({"success": True, "response": response}), 200
