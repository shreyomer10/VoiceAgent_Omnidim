from flask import Blueprint, request, jsonify,make_response,current_app as app
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError
from tokenCheck import token_required
from db import DB_NAME,MONGO_URI

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

products = db["products"]
bids = db["bids"]
auctions = db["auctions"]
users=db["users"]
admins=db["admins"]
transactions=db["transactions"]

wallet_bp = Blueprint('wallet', __name__)

@wallet_bp.route("/wallet", methods=["GET"])
def get_wallet():
    data = request.json
    username = data.get("username")

    if not username:
        return jsonify({"error": "Username is required"}), 400

    user = users.find_one({"username": username})

    if not user:
        return jsonify({"error": "User not found"}), 404

    wallet_balance = user.get("wallet_balance", 0.0)

    return jsonify({
        "wallet_balance": wallet_balance
    }), 200


@wallet_bp.route("/wallet/topup", methods=["POST"])
@token_required
def wallet_topup(decoded_token):
    data = request.json
    amount = data.get("amount")

    if not amount or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    user_id = decoded_token.get("user_id")
    username=decoded_token.get("username")
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401

    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Increase wallet balance
    users.update_one({"_id": ObjectId(user_id)}, {"$inc": {"wallet_balance": amount}})

    # Add transaction
    transactions.insert_one({
        "username": username,
        "type": "topup",
        "amount": amount,
        "timestamp": datetime.utcnow(),
        "meta": {"notes": "Manual top-up"}
    })

    return jsonify({"message": f"₹{amount} added to wallet"}), 200



@wallet_bp.route("/rollback-bid", methods=["POST"])
def rollback_bid():
    data = request.get_json()
    bid_id = data.get("bid_id")
    username = data.get("username")

    if not bid_id or not username:
        return jsonify({"error": "Missing bid_id or username"}), 400

    bid = bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        return jsonify({"error": "Bid not found"}), 404

    # Check product expiry
    product = products.find_one({"id": bid["product_id"]})
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product.get("status") == "sold":
        return jsonify({"error": "Cannot rollback bid. Product already sold."}), 400

    # New: enforce auction’s valid_until instead
    auction = auctions.find_one({"id": product.get("auction_id")})
    if not auction or "valid_until" not in auction:
        return jsonify({"error": "Auction timing not found"}), 400
    try:
        auction_end = datetime.fromisoformat(auction["valid_until"])
    except ValueError:
        return jsonify({"error": "Invalid auction end time format"}), 400
    if datetime.utcnow() >= auction_end:
        return jsonify({"error": "Cannot rollback bid. Auction has ended."}), 400

    amount = bid["amount"]

    # Refund wallet
    users.update_one({"username": username}, {"$inc": {"wallet_balance": amount}})

    # Remove bid from bids collection
    bids.delete_one({"_id": ObjectId(bid_id)})

    # Remove from embedded product bids
    products.update_one(
        {"id": bid["product_id"]},
        {"$pull": {"bids": {"amount": amount, "user_id": username}}}
    )

    # Log the rollback
    transactions.insert_one({
        "username": username,
        "type": "refund",
        "amount": amount,
        "timestamp": datetime.utcnow(),
        "meta": {
            "product_id": bid["product_id"],
            "notes": f"Rollback of bid {str(bid_id)}"
        }
    })

    return jsonify({"message": "Bid rolled back and wallet refunded."}), 200



@wallet_bp.route("/wallet/transactions", methods=["GET"])
@token_required
def get_wallet_transactions(decoded_token):
    user_id = decoded_token.get("user_id")
    username = decoded_token.get("username")

    if not user_id:
        return jsonify({"error": "Invalid token: missing user_id"}), 401

    try:
        logs = list(transactions.find({"username": username}).sort("timestamp", -1))

        for tx in logs:
            tx["_id"] = str(tx["_id"])
            tx["timestamp"] = tx["timestamp"].isoformat()
        
        return jsonify({
            "user_id": user_id,
            "count": len(logs),
            "transactions": logs
        }), 200

    except PyMongoError as e:
        app.logger.error(f"Database error fetching transactions: {str(e)}")
        return jsonify({"error": "Failed to fetch transactions"}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error in get_wallet_transactions: {str(e)}")
        return jsonify({"error": "Unexpected error occurred"}), 500

