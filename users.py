from flask import Blueprint, request, jsonify,current_app as app
from pymongo import MongoClient
from datetime import datetime
from pymongo.errors import PyMongoError
from tokenCheck import token_required
from db import DB_NAME,MONGO_URI,db
from bson import ObjectId

# client = MongoClient(MONGO_URI)
# db = client[DB_NAME]
user_bp = Blueprint('users', __name__)
products = db["products"]
bids = db["bids"]
auctions = db["auctions"]
users=db["users"]
admins=db["admins"]
transactions=db["transactions"]




# 1️⃣ Get all auctions (upcoming & live)
@user_bp.route("/auctions", methods=["GET"])
def list_auctions():
    now = datetime.utcnow().isoformat()
    data = auctions.find({"valid_until": {"$gt": now}})
    return jsonify([{"id":a["id"],"name":a["name"],"valid_until":a["valid_until"]} for a in data]), 200

# 2️⃣ Get products by auction
@user_bp.route("/auctions/<auction_id>/products", methods=["GET"])
def list_auction_products(auction_id):
    prods = products.find({"auction_id": auction_id, "status":"unsold"})
    return jsonify([{"id":p["id"],"name":p["name"]} for p in prods]), 200

# 3️⃣ Register for auction
@user_bp.route("/auctions/register", methods=["POST"])
@token_required
def register_auction(decoded_token):
    data = request.get_json()
    aid = data.get("auction_id")
    if not aid:
        return jsonify({"error": "auction_id required"}), 400

    user_id = decoded_token["user_id"]
    username = decoded_token["username"]

    try:
        # 1️⃣ Check if auction exists
        auction = auctions.find_one({"id": aid})
        if not auction:
            return jsonify({"error": "Auction not found"}), 404

        # 2️⃣ Check if auction is still valid (not expired)
        try:
            auction_end = datetime.fromisoformat(auction.get("valid_until"))
        except Exception:
            return jsonify({"error": "Invalid auction end date format"}), 500

        if datetime.utcnow() >= auction_end:
            return jsonify({"error": "Auction has already ended"}), 400

        # 3️⃣ Check if user already registered
        if user_id in auction.get("registrations", []):
            return jsonify({"message": "User already registered for this auction"}), 200

        # 4️⃣ Add user to auction's registrations
        auctions.update_one(
            {"id": aid},
            {"$addToSet": {"registrations": user_id}}
        )

        # 5️⃣ Add auction_id to user's auctions list
        users.update_one(
            {"_id": ObjectId(user_id)},
            {"$addToSet": {"auctions": aid}}
        )

        return jsonify({"message": "Successfully registered for auction"}), 200

    except Exception as e:
        app.logger.error(f"Error in register_auction: {str(e)}")
        return jsonify({"error": "Failed to register for auction"}), 500

@user_bp.route("/bid", methods=["POST"])
def place_bid():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # Extract inputs
        product_key = data.get("product_name")
        bid_amount = data.get("bid_amount")
        username = data.get("user_id")
        now = datetime.utcnow()

        # Validate inputs
        if not all([product_key, bid_amount is not None, username]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # 1️⃣ Validate User
        user = users.find_one({"username": username})
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        if user.get("wallet_balance", 0) < bid_amount:
            return jsonify({"success": False, "message": "Insufficient wallet balance"}), 400

        # 2️⃣ Resolve Product
        try:
            prod_id_int = int(product_key)
        except (ValueError, TypeError):
            prod_id_int = None

        product = products.find_one({
            "$or": [
                {"id": product_key},
                {"id": prod_id_int},
                {"name": product_key}
            ]
        })
        if not product:
            return jsonify({"success": False, "message": "Product not found"}), 404

        if product.get("status") == "sold":
            return jsonify({"success": False, "message": "Product already sold"}), 400

        auction_id = product.get("auction_id")
        if not auction_id:
            return jsonify({"success": False, "message": "Product is not part of an auction"}), 400

        # 3️⃣ Validate Auction
        auction = auctions.find_one({"id": auction_id})
        if not auction:
            return jsonify({"success": False, "message": "Auction not found"}), 404

        # 🔒 Check auction is still active
        try:
            auction_end = datetime.fromisoformat(auction["valid_until"])
        except Exception:
            return jsonify({"success": False, "message": "Invalid auction end time"}), 500

        if now >= auction_end:
            products.update_one({"id": product["id"]}, {"$set": {"status": "sold"}})
            return jsonify({"success": False, "message": "Auction has ended"}), 400

        user_id_str = str(user.get("_id"))
        registrations = [str(r) for r in auction.get("registrations", [])]

        if user_id_str not in registrations:
            return jsonify({"success": False, "message": "User not registered for this auction"}), 403

        # 4️⃣ Check Highest Bid
        embedded_bids = product.get("bids", [])
        max_bid = max([b.get("amount", 0) for b in embedded_bids], default=0)

        if bid_amount <= max_bid:
            return jsonify({
                "success": False,
                "message": f"Bid must be higher than current max of ₹{max_bid}"
            }), 400

        # 5️⃣ Deduct wallet balance
        users.update_one({"username": username}, {"$inc": {"wallet_balance": -bid_amount}})

        # 6️⃣ Record the bid
        bid_entry = {
            "product_id": product.get("id"),
            "product_name": product.get("name"),
            "auction_id": auction_id,
            "amount": bid_amount,
            "timestamp": now,
            "status": "success",
            "user_id": username
        }
        bids.insert_one(bid_entry)

        # 7️⃣ Log transaction
        transactions.insert_one({
            "username": username,
            "type": "bid",
            "amount": bid_amount,
            "timestamp": now,
            "meta": {
                "product_id": product.get("id"),
                "notes": f"Bid placed on {product.get('name')}"
            }
        })

        # 8️⃣ Add to embedded product bids
        products.update_one(
            {"_id": product["_id"]},
            {"$push": {
                "bids": {
                    "amount": bid_amount,
                    "timestamp": now,
                    "user_id": username
                }
            }}
        )

        return jsonify({"success": True, "message": "Bid placed successfully"}), 201

    except Exception as e:
        app.logger.error(f"Error in place_bid: {str(e)}")
        return jsonify({"success": False, "message": "Unexpected error occurred"}), 500

@user_bp.route("/user-bids", methods=["GET"])
@token_required
def get_user_bids(decoded_token):
    try:
        username = decoded_token.get("username")
        if not username:
            return jsonify({"error": "Invalid token: missing username"}), 401

        try:
            bid_query = {"user_id": username}
            bid_list = bids.find(bid_query).sort("timestamp", -1)

            result = []
            for b in bid_list:
                result.append({
                    "bid_id": str(b.get("_id")),
                    "product_id": b.get("product_id"),
                    "product_name": b.get("product_name"),
                    "auction_id": b.get("auction_id"),
                    "amount": b.get("amount"),
                    "timestamp": b.get("timestamp").isoformat() if b.get("timestamp") else None,
                    "status": b.get("status", "success")
                })

            return jsonify(result), 200

        except Exception as e:
            app.logger.error(f"Database error fetching user bids: {str(e)}")
            return jsonify({"error": "Failed to fetch user bids due to database error"}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error in get_user_bids: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@user_bp.route("/bids", methods=["GET"])
def get_all_bids():
    try:
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

        try:
            product = products.find_one(query)
            if not product:
                return jsonify({"error": "Product not found"}), 404

            bid_query = {
                "$or": [
                    {"product_id": product.get("id")},
                    {"product_name": product.get("name")}
                ]
            }

            try:
                bid_list = bids.find(bid_query).sort("timestamp", -1)
                result = []
                for b in bid_list:
                    result.append({
                        "amount": b.get("amount"),  # Fixed from bid_amount to amount
                        "user_id": b.get("user_id"),  # Changed from user_mobile to user_id
                        "timestamp": b.get("timestamp").isoformat() if b.get("timestamp") else None,
                        "status": b.get("status", "success")
                    })
                return jsonify(result), 200
            except PyMongoError as e:
                app.logger.error(f"Database error fetching bids: {str(e)}")
                return jsonify({"error": "Failed to fetch bids due to database error"}), 500

        except PyMongoError as e:
            app.logger.error(f"Database error finding product: {str(e)}")
            return jsonify({"error": "Failed to find product due to database error"}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error in get_all_bids: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@user_bp.route("/highest-bid", methods=["GET"])
def get_highest_bid():
    try:
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

        try:
            product = products.find_one(query)
            if not product:
                return jsonify({"error": "Product not found"}), 404

            embedded_bids = product.get("bids", [])
            max_bid = max([b.get("amount", 0) for b in embedded_bids], default=0)

            return jsonify({
                "product": product["name"],
                "highest_bid": max_bid
            }), 200
        except PyMongoError as e:
            app.logger.error(f"Database error in get_highest_bid: {str(e)}")
            return jsonify({"error": "Failed to fetch highest bid due to database error"}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error in get_highest_bid: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@user_bp.route("/time-left", methods=["GET"])
def get_time_left():
    try:
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

        try:
            product = products.find_one(query)
            if not product:
                return jsonify({"error": "Product not found"}), 404
            
            # Fetch the parent auction
            auction = auctions.find_one({"id": product.get("auction_id")})
            if not auction or "valid_until" not in auction:
                return jsonify({"error": "Auction end time not set"}), 400
            try:
                auction_end = datetime.fromisoformat(auction["valid_until"])
            except ValueError as e:
                return jsonify({"error": f"Invalid auction end time: {e}"}), 400

            now = datetime.utcnow()
            time_left = (auction_end - now).total_seconds()
            time_left = max(int(time_left), 0)
            
            return jsonify({
                "product": product["name"],
                "time_remaining_seconds": time_left
            }), 200
        except PyMongoError as e:
            app.logger.error(f"Database error in get_time_left: {str(e)}")
            return jsonify({"error": "Failed to fetch time left due to database error"}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error in get_time_left: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@user_bp.route("/user-bids/auction/<auction_id>", methods=["GET"])
@token_required
def get_user_bids_for_auction(decoded_token, auction_id):
    if not auction_id:
        return jsonify({"error": "Missing auction_id in path."}), 400

    try:
        # ✅ Check if auction exists
        auction = auctions.find_one({"id": auction_id})
        if not auction:
            return jsonify({"error": f"Auction with id '{auction_id}' not found."}), 404

        # ✅ Fetch user-specific bids for this auction
        query = {
            "user_id": decoded_token["username"],
            "auction_id": auction_id
        }
        bid_list = bids.find(query).sort("timestamp", -1)

        result = []
        for b in bid_list:
            result.append({
                "bid_id": str(b.get("_id")),
                "product_id": b.get("product_id"),
                "product_name": b.get("product_name"),
                "amount": b.get("amount"),
                "timestamp": b.get("timestamp").isoformat() if b.get("timestamp") else None,
                "status": b.get("status", "success")
            })

        return jsonify(result), 200

    except Exception as e:
        app.logger.error(f"Error in get_user_bids_for_auction: {str(e)}")
        return jsonify({"error": "Failed to fetch user bids for this auction"}), 500
