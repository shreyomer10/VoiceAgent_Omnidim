from flask import Flask, jsonify
import pytz
from flask_cors import CORS
from admins import admin_bp
from auth import auth_bp
from wallet import wallet_bp
from users import user_bp

app = Flask(__name__)
app.register_blueprint(admin_bp, url_prefix='/')
app.register_blueprint(auth_bp, url_prefix='/')
app.register_blueprint(wallet_bp, url_prefix='/')
app.register_blueprint(user_bp, url_prefix='/')

from flask_cors import CORS

CORS(app,
     supports_credentials=True,
     origins="*",
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

utc = pytz.utc


@app.route("/")
def home():
    return jsonify({
  "message": "Complete CodeClash Auction System API Documentation",
  "endpoints": {
    "authentication": {
      "user_registration": {
        "method": "POST",
        "path": "/register",
        "description": "Register a new user",
        "sample_request": {
          "name": "John Doe",
          "username": "johndoe",
          "password": "securepassword123",
          "mobile_number": "9876543210"
        }
      },
      "user_login": {
        "method": "POST",
        "path": "/login",
        "description": "User login",
        "sample_request": {
          "username": "johndoe",
          "password": "securepassword123"
        }
      },
      "change_password": {
        "method": "POST",
        "path": "/change-password",
        "description": "Change user password",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "username": "johndoe",
          "password": "oldpassword",
          "new_password": "newsecurepassword456"
        }
      },
      "admin_registration": {
        "method": "POST",
        "path": "/admin/register",
        "description": "Register a new admin",
        "sample_request": {
          "name": "Admin User",
          "username": "admin",
          "password": "adminpassword123",
          "mobile_number": "9876543210",
          "role": "admin"
        }
      },
      "admin_login": {
        "method": "POST",
        "path": "/admin/login",
        "description": "Admin login",
        "sample_request": {
          "username": "admin",
          "password": "adminpassword123",
          "role": "admin"
        }
      },
      "admin_change_password": {
        "method": "POST",
        "path": "/admin/change-password",
        "description": "Change admin password",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "username": "admin",
          "password": "oldadminpassword",
          "new_password": "newadminpassword456",
          "role": "admin"
        }
      }
    },
    "user_operations": {
      "list_auctions": {
        "method": "GET",
        "path": "/auctions",
        "description": "List all active auctions"
      },
      "list_auction_products": {
        "method": "GET",
        "path": "/auctions/<auction_id>/products",
        "description": "List products in an auction",
        "example": "/auctions/123/products"
      },
      "register_for_auction": {
        "method": "POST",
        "path": "/auctions/register",
        "description": "Register user for an auction",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "auction_id": "123"
        }
      },
      "place_bid": {
        "method": "POST",
        "path": "/bid",
        "description": "Place a bid on a product",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "product_name": "Product 1",
          "bid_amount": 1500,
          "user_id": "johndoe"
        }
      },
      "get_user_bids": {
        "method": "GET",
        "path": "/user-bids",
        "description": "Get all bids by the current user",
        "headers": {
          "Authorization": "Bearer <token>"
        }
      },
      "get_user_bids_for_auction": {
        "method": "GET",
        "path": "/user-bids/auction/<auction_id>",
        "description": "Get user's bids for specific auction",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "example": "/user-bids/auction/123"
      },
      "get_all_bids": {
        "method": "GET",
        "path": "/bids",
        "description": "Get all bids for a product",
        "query_params": {
          "product_key": "product_id_or_name"
        },
        "example": "/bids?product_key=prod1"
      },
      "get_highest_bid": {
        "method": "GET",
        "path": "/highest-bid",
        "description": "Get highest bid for a product",
        "query_params": {
          "product_key": "product_id_or_name"
        },
        "example": "/highest-bid?product_key=prod1"
      },
      "get_time_left": {
        "method": "GET",
        "path": "/time-left",
        "description": "Get time remaining for a product's auction",
        "query_params": {
          "product_key": "product_id_or_name"
        },
        "example": "/time-left?product_key=prod1"
      }
    },
    "wallet_operations": {
      "get_wallet_balance": {
        "method": "GET",
        "path": "/wallet",
        "description": "Get user's wallet balance",
        "sample_request": {
          "username": "johndoe"
        }
      },
      "wallet_topup": {
        "method": "POST",
        "path": "/wallet/topup",
        "description": "Add funds to wallet",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "amount": 1000
        }
      },
      "get_wallet_transactions": {
        "method": "GET",
        "path": "/wallet/transactions",
        "description": "Get wallet transaction history",
        "headers": {
          "Authorization": "Bearer <token>"
        }
      },
      "rollback_bid": {
        "method": "POST",
        "path": "/rollback-bid",
        "description": "Cancel/refund a bid",
        "sample_request": {
          "bid_id": "507f1f77bcf86cd799439011",
          "username": "johndoe"
        }
      }
    },
    "admin_operations": {
      "create_auction": {
        "method": "POST",
        "path": "/admin/auction",
        "description": "Create a new auction",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "id": "auction123",
          "name": "Summer Auction",
          "product_ids": ["prod1", "prod2"],
          "valid_until": "2023-12-31T23:59:59"
        }
      },
      "update_auction": {
        "method": "PUT",
        "path": "/admin/auction/<auction_id>",
        "description": "Update an existing auction",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "name": "Updated Auction Name",
          "product_ids": ["prod1", "prod2", "prod3"],
          "valid_until": "2023-12-31T23:59:59"
        },
        "example": "/admin/auction/auction123"
      },
      "delete_auction": {
        "method": "DELETE",
        "path": "/admin/auction/<auction_id>",
        "description": "Delete an auction",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "example": "/admin/auction/auction123"
      },
      "add_product": {
        "method": "POST",
        "path": "/admin/product",
        "description": "Add a new product",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "id": "prod1",
          "name": "Product 1",
          "description": "Description of product"
        }
      },
      "update_product": {
        "method": "PUT",
        "path": "/admin/product/<product_id>",
        "description": "Update a product",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "sample_request": {
          "name": "Updated Product Name",
          "description": "Updated description",
          "auction_id": "auction123"
        },
        "example": "/admin/product/prod1"
      },
      "delete_product": {
        "method": "DELETE",
        "path": "/admin/product/<product_id>",
        "description": "Delete a product",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "example": "/admin/product/prod1"
      },
      "get_all_auctions": {
        "method": "GET",
        "path": "/admin/all_auctions",
        "description": "Get all auctions (admin view)"
      },
      "get_auction_products": {
        "method": "GET",
        "path": "/admin/auction_products/<auction_id>",
        "description": "Get products in an auction (admin view)",
        "example": "/admin/auction_products/auction123"
      },
      "list_unassigned_products": {
        "method": "GET",
        "path": "/admin/products/unassigned",
        "description": "List products not assigned to any auction",
        "headers": {
          "Authorization": "Bearer <token>"
        }
      },
      "get_my_auctions": {
        "method": "GET",
        "path": "/admin/auctions/my",
        "description": "Get auctions created by current admin",
        "headers": {
          "Authorization": "Bearer <token>"
        }
      },
      "get_auction_products_admin": {
        "method": "GET",
        "path": "/admin/auction/<auction_id>/products",
        "description": "Get products in auction (admin-specific view)",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "example": "/admin/auction/auction123/products"
      },
      "settle_auction": {
        "method": "POST",
        "path": "/admin/auction/<auction_id>/settle",
        "description": "Finalize auction and determine winners",
        "headers": {
          "Authorization": "Bearer <token>"
        },
        "example": "/admin/auction/auction123/settle"
      }
    }
  },
  "notes": [
    "All endpoints returning user-specific data require JWT authentication in Authorization header",
    "Admin endpoints require admin privileges",
    "Timestamps should be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)",
    "For POST/PUT requests, include Content-Type: application/json header",
    "Error responses typically include {error: message} or {success: bool, message: string} format"
  ],
  "collections": {
    "database_collections_used": [
      "users",
      "admins",
      "auctions",
      "products",
      "bids",
      "transactions"
    ]
  }
}), 200


if __name__ == "__main__":
    app.run(debug=True)
