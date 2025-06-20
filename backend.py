from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import pytz
import os
from flask_cors import CORS
# Load environment variables
load_dotenv()

# Setup
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
products = db["products"]
bids = db["bids"]

app = Flask(__name__)
CORS(app)
utc = pytz.utc


@app.route("/")
def home():
    return "Welcome to CodeClash Auction Table"
# 1. GET all products and details
@app.route("/products", methods=["GET"])
def get_products():
    data = products.find()
    result = []
    for p in data:
        result.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "description": p.get("description"),
            "auction_end_time": p.get("auction_end_time")
        })
    return jsonify(result)

# 2. POST a bid
@app.route("/bid", methods=["POST"])
def place_bid():
    data = request.json
    #product_key = data.get("product_id")
    product_key = data.get("product_name")
    bid_amount = data.get("bid_amount")


    try:
        product_id = int(product_key)
    except ValueError:
        product_id = None

    if not (product_key) or not bid_amount:
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    # Search by id or name
    query = {
        "$or": [
            {"id": str(product_key)},    # for string ID
            {"id": product_id},          # for numeric ID
            {"name": product_key}        # match by name
        ]
    }
    product = products.find_one(query)

    if not product:
        return jsonify({"success": False, "message": "Product not found."}), 404

    # Find max bid from product's embedded bids
    embedded_bids = product.get("bids", [])
    max_bid = max([b.get("amount", 0) for b in embedded_bids], default=0)

    if bid_amount <= max_bid:
        return jsonify({
            "success": False,
            "message": f"Bid must be higher than current max of {max_bid}."
        }), 400

    timestamp = datetime.utcnow()

    # Insert into bids collection
    bid_entry = {
        "product_id": product.get("id"),
        "product_name": product.get("name"),
        "amount": bid_amount,
        "status": "success",
        "timestamp": timestamp
    }
    bids.insert_one(bid_entry)

    # Update product's embedded bid array
    products.update_one(
        {"_id": product["_id"]},
        {"$push": {"bids": {
            "amount": bid_amount,
            "timestamp": timestamp
        }}}
    )

    return jsonify({"success": True, "message": "Bid placed successfully."})

# 3. GET highest bid for product
@app.route("/highest-bid", methods=["GET"])
def get_highest_bid():
    product_key = request.args.get("product_key")

    if not product_key:
        return jsonify({"error": "Missing product_key in query."}), 400

    try:
        product_id = int(product_key)
    except ValueError:
        product_id = None

    query = {
        "$or": [
            {"id": str(product_key)},
            {"id": product_id},
            {"name": product_key}
        ]
    }

    product = products.find_one(query)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    embedded_bids = product.get("bids", [])
    max_bid = max([b.get("amount", 0) for b in embedded_bids], default=0)

    return jsonify({
        "product": product["name"],
        "highest_bid": max_bid
    })

# 4. GET time left for product
@app.route("/time-left", methods=["GET"])
def get_time_left():
    product_key = request.args.get("product_key")

    if not product_key:
        return jsonify({"error": "Missing product_key in query."}), 400

    try:
        product_id = int(product_key)
    except ValueError:
        product_id = None

    query = {
        "$or": [
            {"id": str(product_key)},
            {"id": product_id},
            {"name": product_key}
        ]
    }

    product = products.find_one(query)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    auction_end = product.get("auction_end_time")
    if not auction_end:
        return jsonify({"error": "Auction end time not set"}), 400
    try:
        # Convert ISO string to datetime
        auction_end = datetime.fromisoformat(auction_end)
    except Exception as e:
        return jsonify({"error": f"Invalid date format: {str(e)}"}), 400

    now = datetime.utcnow()
    time_left = (auction_end - now).total_seconds()
    time_left = max(int(time_left), 0)

    return jsonify({
        "product": product["name"],
        "time_remaining_seconds": time_left
    })
@app.route("/bids", methods=["GET"])
def get_all_bids():
    product_key = request.args.get("product_key")

    if not product_key:
        return jsonify({"error": "Missing product_key in query."}), 400

    try:
        product_id = int(product_key)
    except ValueError:
        product_id = None

    query = {
        "$or": [
            {"id": str(product_key)},
            {"id": product_id},
            {"name": product_key}
        ]
    }

    product = products.find_one(query)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    bid_list = bids.find({
        "$or": [
            {"product_id": product.get("id")},
            {"product_name": product.get("name")}
        ]
    }).sort("timestamp", -1)

    result = []
    for b in bid_list:
        result.append({
            "amount": b.get("bid_amount"),
            "user_mobile": b.get("user_mobile"),
            "timestamp": b.get("timestamp"),
            "status": b.get("status", "success")
        })

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)




        
