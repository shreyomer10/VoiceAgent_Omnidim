from flask import Blueprint, request, jsonify,current_app as app
from pymongo import MongoClient
from datetime import datetime
from pymongo.errors import PyMongoError
from tokenCheck import token_required
from db import DB_NAME,MONGO_URI,db

# client = MongoClient(MONGO_URI)
# db = client[DB_NAME]
admin_bp = Blueprint('admin', __name__)
products = db["products"]
bids = db["bids"]
auctions = db["auctions"]
users=db["users"]
admins=db["admins"]
transactions=db["transactions"]

# Admin routes
# 1️⃣ Create Auction
@admin_bp.route("/admin/auction", methods=["POST"])
@token_required
def create_auction(decoded_token):
    data = request.get_json()
    # expect: id, name, product_ids (list), valid_until (ISO), optional 'time'
    for f in ("id","name","product_ids","valid_until"):
        if f not in data:
            return jsonify({"error": f"{f} required"}), 400

    auction = {
        "id": data["id"],
        "name": data["name"],
        "product_ids": data["product_ids"],
        "valid_until": data["valid_until"],
        "registrations": [],              # new empty list
        "created_by": decoded_token["admin_id"],
        "time_created": datetime.utcnow(),
        "settled": False,
        "settled_at": None,
    }
    try:
        auctions.insert_one(auction)
        # link products
        products.update_many(
            {"id": {"$in": auction["product_ids"]}},
            {"$set": {
                "auction_id": auction["id"],
                "sold_to": None,
                "admin_id": decoded_token["admin_id"]
            }}
        )
        return jsonify({"message":"Auction created"}), 201
    except PyMongoError as e:
        app.logger.error(str(e))
        return jsonify({"error":"Failed to create auction"}), 500

@admin_bp.route("/admin/product/<product_id>", methods=["PUT"])
@token_required
def update_product(decoded_token, product_id):
    try:
        # 1) Validate ID and payload
        if not product_id:
            return jsonify({"success": False, "message": "Missing product_id"}), 400
        data = request.get_json() or {}
        allowed = {k: v for k, v in data.items() if k in ("name", "description", "auction_id")}
        if not allowed:
            return jsonify({"success": False, "message": "No valid fields to update"}), 400

        # 2) Ensure product exists
        prod = products.find_one({"id": product_id})
        if not prod:
            return jsonify({"success": False, "message": "Product not found"}), 404

        # 3) Perform update
        try:
            res = products.update_one({"id": product_id}, {"$set": allowed})
            if res.modified_count == 0:
                return jsonify({"success": False, "message": "No changes made to product"}), 200
            return jsonify({"success": True, "message": "Product updated."}), 200

        except PyMongoError as e:
            app.logger.error(f"Database error in update_product: {e}")
            return jsonify({"success": False, "message": "Failed to update product"}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error in update_product: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@admin_bp.route("/admin/auction/<auction_id>", methods=["PUT"])
@token_required
def update_auction(decoded_token, auction_id):
    try:
        # 1) Validate ID and payload
        if not auction_id:
            return jsonify({"success": False, "message": "Missing auction_id"}), 400
        data = request.get_json() or {}
        allowed = {k: v for k, v in data.items() if k in ("name", "product_ids", "valid_until")}
        if not allowed:
            return jsonify({"success": False, "message": "No valid fields to update"}), 400

        # 2) Ensure auction exists
        old_auction = auctions.find_one({"id": auction_id})
        if not old_auction:
            return jsonify({"success": False, "message": "Auction not found"}), 404

        # 3) Apply core auction update
        try:
            res = auctions.update_one({"id": auction_id}, {"$set": allowed})
            if res.modified_count == 0:
                return jsonify({"success": False, "message": "No changes made to auction"}), 200

        except PyMongoError as e:
            app.logger.error(f"Database error in update_auction: {e}")
            return jsonify({"success": False, "message": "Failed to update auction"}), 500

        # 4) If product_ids changed, relink products
        if "product_ids" in allowed:
            try:
                # Unlink all previously linked products
                products.update_many(
                    {"auction_id": auction_id},
                    {"$set": {"auction_id": None}}
                )
                # Link new batch
                products.update_many(
                    {"id": {"$in": allowed["product_ids"]}},
                    {"$set": {"auction_id": auction_id}}
                )

            except PyMongoError as e:
                app.logger.error(f"Failed to update product links: {e}")
                # Revert auction update
                auctions.update_one({"id": auction_id}, {"$set": old_auction})
                return jsonify({"success": False, "message": "Failed to update product links"}), 500

        return jsonify({"success": True, "message": "Auction updated."}), 200

    except Exception as e:
        app.logger.error(f"Unexpected error in update_auction: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@admin_bp.route("/admin/auction/<auction_id>", methods=["DELETE"])
@token_required
def delete_auction(decoded_token, auction_id):
    try:
        if not auction_id:
            return jsonify({"success": False, "message": "Missing auction_id"}), 400

        # 1) Ensure it exists
        auc = auctions.find_one({"id": auction_id})
        if not auc:
            return jsonify({"success": False, "message": "Auction not found"}), 404

        # 2) Unlink products
        try:
            products.update_many(
                {"auction_id": auction_id},
                {"$set": {"auction_id": None}}
            )
        except PyMongoError as e:
            app.logger.error(f"Failed to unlink products: {e}")
            return jsonify({"success": False, "message": "Failed to unlink products"}), 500

        # 3) Delete the auction
        try:
            auctions.delete_one({"id": auction_id})
        except PyMongoError as e:
            app.logger.error(f"Failed to delete auction: {e}")
            return jsonify({"success": False, "message": "Failed to delete auction"}), 500

        # 4) Cleanup bids (optional)
        try:
            bids.delete_many({"auction_id": auction_id})
        except PyMongoError as e:
            app.logger.error(f"Failed to delete related bids: {e}")
            # continue — auction deletion succeeded

        return jsonify({"success": True, "message": "Auction deleted and products unlinked."}), 200

    except Exception as e:
        app.logger.error(f"Unexpected error in delete_auction: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@admin_bp.route("/admin/product/<product_id>", methods=["DELETE"])
@token_required
def delete_product(decoded_token, product_id):
    try:
        if not product_id:
            return jsonify({"success": False, "message": "Missing product_id"}), 400

        # 1) Ensure exists
        prod = products.find_one({"id": product_id})
        if not prod:
            return jsonify({"success": False, "message": "Product not found"}), 404

        # 2) Delete the product
        try:
            products.delete_one({"id": product_id})
        except PyMongoError as e:
            app.logger.error(f"Failed to delete product: {e}")
            return jsonify({"success": False, "message": "Failed to delete product"}), 500

        # 3) Remove from auctions' product_ids
        try:
            auctions.update_many(
                {},
                {"$pull": {"product_ids": product_id}}
            )
        except PyMongoError as e:
            app.logger.error(f"Failed to remove product from auctions: {e}")
            # continue — product deletion succeeded

        # 4) Cleanup bids
        try:
            bids.delete_many({"product_id": product_id})
        except PyMongoError as e:
            app.logger.error(f"Failed to delete related bids: {e}")
            # continue

        return jsonify({"success": True, "message": "Product deleted and removed from auctions."}), 200

    except Exception as e:
        app.logger.error(f"Unexpected error in delete_product: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500

@admin_bp.route("/admin/product", methods=["POST"])
@token_required
def add_product(decoded_token):
    data = request.get_json()
    for f in ("id","name","description"):
        if f not in data:
            return jsonify({"error":f"{f} required"}), 400

    prod = {
        "id": data["id"],
        "name": data["name"],
        "description": data["description"],
        "auction_id": None,
        "sold_to": None,
        "admin_id": decoded_token["admin_id"],
        "status": "unsold",
        "bids": []
    }
    try:
        products.insert_one(prod)
        return jsonify({"message":"Product added"}), 201
    except PyMongoError as e:
        app.logger.error(str(e))
        return jsonify({"error":"Failed to add product"}), 500


@admin_bp.route("/admin/all_auctions", methods=["GET"])
def get_all_auctions():
    try:
        auction_list = list(auctions.find({}))
        result = []
        for a in auction_list:
            result.append({
                "id": a.get("id"),
                "name": a.get("name"),
                "valid_until": a.get("valid_until"),
                "product_ids": a.get("product_ids", [])
            })
        return jsonify({
            "total_auctions": len(result),
            "auctions": result
        }), 200

    except Exception as e:
        app.logger.error(f"Error fetching auctions: {str(e)}")
        return jsonify({"error": "Failed to fetch auctions"}), 500


@admin_bp.route("/admin/auction_products/<auction_id>", methods=["GET"])
def get_products_by_auction(auction_id):
    try:
        matching_products = list(products.find({"auction_id": auction_id}))
        result = []
        for p in matching_products:
            result.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "description": p.get("description"),
                "status": p.get("status"),
                "time": p.get("time")
            })
        return jsonify({
            "auction_id": auction_id,
            "total_products": len(result),
            "products": result
        }), 200

    except Exception as e:
        app.logger.error(f"Error fetching products for auction {auction_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch products for the given auction"}), 500


@admin_bp.route("/admin/products/unassigned", methods=["GET"])
@token_required
def list_unassigned_products(decoded_token):
    prods = products.find({
        "admin_id": decoded_token["admin_id"],
        "auction_id": None,
        "status": "unsold"
    })
    return jsonify([{
        "id": p["id"], "name": p["name"], "description": p["description"]
    } for p in prods]), 200

@admin_bp.route("/admin/auction/<auction_id>/products", methods=["GET"])
@token_required
def get_my_products( decoded_token,auction_id):
    # ensure auction belongs to admin?
    prods = products.find({"auction_id": auction_id})
    return jsonify([{"id":p["id"],"name":p["name"],"status":p["status"]} for p in prods]), 200

@admin_bp.route("/admin/auctions/my", methods=["GET"])
@token_required
def get_my_auctions(decoded_token):
    my = auctions.find({"created_by": decoded_token["admin_id"]})
    return jsonify([{
        "id": a["id"], "name": a["name"], "valid_until": a["valid_until"]
    } for a in my]), 200

@admin_bp.route("/admin/auction/<auction_id>/settle", methods=["POST"])
@token_required
def settle_auction(decoded_token, auction_id):
    from datetime import datetime

    # 1️⃣ Fetch the auction
    auction = auctions.find_one({"id": auction_id, "created_by": decoded_token["admin_id"]})
    if not auction:
        return jsonify({"error": "Auction not found or unauthorized"}), 404

    # 2️⃣ Check if already settled
    if auction.get("settled", False):
        return jsonify({"error": "Auction is already settled"}), 400

    # 3️⃣ Check if auction has products
    if not auction.get("product_ids") or not isinstance(auction["product_ids"], list):
        return jsonify({"error": "Auction has no products to settle"}), 400

    # 4️⃣ Check if auction is expired
    try:
        auction_end_time = datetime.fromisoformat(auction["valid_until"])
    except Exception:
        return jsonify({"error": "Invalid auction end time format"}), 500

    now = datetime.utcnow()
    if now < auction_end_time:
        return jsonify({"error": "Auction is still active"}), 400

    # 5️⃣ For each product in this auction, ensure it exists
    missing_products = []
    settled_products = []

    for product_id in auction["product_ids"]:
        product = products.find_one({"id": product_id})
        if not product:
            missing_products.append(product_id)
            continue

        # 6️⃣ Find highest bid
        highest_bid = bids.find_one(
            {"product_id": product_id},
            sort=[("amount", -1)]
        )

        if highest_bid:
            update_result = products.update_one(
                {"id": product_id},
                {"$set": {
                    "status": "sold",
                    "sold_to": highest_bid["user_id"]
                }}
            )
            settled_products.append({"product_id": product_id, "status": "sold", "sold_to": highest_bid["user_id"]})
        else:
            update_result = products.update_one(
                {"id": product_id},
                {"$set": {
                    "status": "unsold",
                    "sold_to": None
                }}
            )
            settled_products.append({"product_id": product_id, "status": "unsold", "sold_to": None})

    # 7️⃣ Mark auction as settled
    auctions.update_one(
        {"id": auction_id},
        {"$set": {"settled": True, "settled_at": datetime.utcnow()}}
    )

    # 8️⃣ Return detailed result
    return jsonify({
        "message": "Auction settled successfully",
        "settled_products": settled_products,
        "missing_products": missing_products
    }), 200
