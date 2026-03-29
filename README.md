# PG Life — Backend API (Python Flask)

Built with **Flask + PyMongo + MongoDB + JWT**

## 📁 Folder Structure
```
backend/
├── app.py                         # Flask app entry point
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
│
├── config/
│   └── db.py                      # Cloudinary config + upload helper
│
├── controllers/
│   ├── auth_controller.py         # OTP send/verify, JWT, profile
│   ├── listing_controller.py      # CRUD + multi-filter search
│   ├── wishlist_controller.py     # Save/unsave listings
│   ├── review_controller.py       # Reviews + avg rating update
│   ├── owner_controller.py        # Dashboard stats + listing toggle
│   └── chat_controller.py         # NLP chatbot intent parsing
│
├── middleware/
│   └── auth_middleware.py         # login_required, owner_only, optional_auth decorators
│
├── routes/
│   ├── auth_routes.py
│   ├── listing_routes.py
│   ├── wishlist_routes.py
│   ├── review_routes.py
│   ├── owner_routes.py
│   └── chat_routes.py
│
└── utils/
    └── helpers.py                 # serialize(), generate_otp(), paginate()
```

## 🚀 Setup & Run

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Fill in MONGO_URI, JWT_SECRET_KEY, Cloudinary keys

# Run
python app.py
# API running at http://localhost:5000
```

## 🔗 API Endpoints

### Auth  `/api/auth`
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/send-otp` | Send OTP to phone number |
| POST | `/verify-otp` | Verify OTP → returns JWT token |
| GET | `/me` | Get logged-in user (JWT required) |
| PUT | `/profile` | Update name/email |

### Listings  `/api/listings`
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Get all listings (with filters) |
| GET | `/map` | Map view listings |
| GET | `/<id>` | Single listing detail |
| POST | `/` | Create listing (owner only) |
| PUT | `/<id>` | Update listing (owner only) |
| DELETE | `/<id>` | Delete listing (owner only) |

### Wishlist  `/api/wishlist`
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Get saved listings |
| POST | `/<id>/toggle` | Save / unsave |

### Reviews  `/api/reviews`
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/<listing_id>` | Get reviews for a listing |
| POST | `/<listing_id>` | Submit review |
| DELETE | `/<review_id>` | Delete own review |

### Owner  `/api/owner`
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/listings` | Owner's all listings |
| GET | `/stats` | Dashboard stats |
| PATCH | `/listings/<id>/toggle` | Toggle active/inactive |

### Chatbot  `/api/chat`
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/message` | Send chat message → NLP response |

## 🔑 Filter Query Params for `GET /api/listings`
```
city        = Noida | Delhi | Gurgaon | Bangalore
gender      = Boys | Girls | Coliving | Any
minBudget   = number
maxBudget   = number
locality    = string (partial match)
amenities   = wifi,ac,food,laundry,gym,cctv,parking
sort        = newest | oldest | price-low | price-high | rating
page        = number (default 1)
limit       = number (default 12)
```

## 🗃 MongoDB Collections
- `users` — Seekers and Owners
- `listings` — PG listings with amenities, images, geo
- `reviews` — User reviews with rating
- `otps` — Temporary OTP storage (TTL recommended)
