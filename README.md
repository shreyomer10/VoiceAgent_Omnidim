
# 🧠 Voice Agent Auction System API

This is the backend API for a real-time auction system using voice interaction. It provides endpoints to manage products, place and view bids, and check auction details.

**Base URL**  
`https://voiceagentomnidim-production.up.railway.app/`

---

## 📂 Endpoints

---

### ✅ Home

**GET /**  
Returns a welcome message.

**Sample Response**
```json
"Welcome to CodeClash Auction Table"
```

---

### 📦 1. Get All Products

**GET /products**  
Returns a list of all auction products with details.

**Response**
```json
[
  {
    "id": 101,
    "name": "iPhone 15",
    "description": "Latest Apple iPhone",
    "auction_end_time": "2025-06-30T18:00:00"
  },
  ...
]
```

---

### 💰 2. Place a Bid

**POST /bid**

**Request Body**
```json
{
  "product_name": "iPhone 15",  // OR "product_id": 101
  "bid_amount": 1200
}
```

**Success Response**
```json
{
  "success": true,
  "message": "Bid placed successfully."
}
```

**Failure Responses**
```json
{
  "success": false,
  "message": "Product not found."
}
```

```json
{
  "success": false,
  "message": "Bid must be higher than current max of 1100."
}
```

```json
{
  "success": false,
  "message": "Missing required fields."
}
```

---

### 🏆 3. Get Highest Bid for a Product

**GET /highest-bid?product_key={product_name_or_id}**

**Sample Request**
```
/highest-bid?product_key=iPhone 15
```

**Response**
```json
{
  "product": "iPhone 15",
  "highest_bid": 1200
}
```

---

### ⏳ 4. Get Time Left for Product Auction

**GET /time-left?product_key={product_name_or_id}**

**Sample Request**
```
/time-left?product_key=101
```

**Response**
```json
{
  "product": "iPhone 15",
  "time_remaining_seconds": 43200
}
```

**Error Response**
```json
{
  "error": "Auction end time not set"
}
```

---

### 📜 5. Get All Bids for a Product

**GET /bids?product_key={product_name_or_id}**

**Sample Request**
```
/bids?product_key=iPhone 15
```

**Response**
```json
[
  {
    "amount": 1200,
    "user_mobile": "9876543210",
    "timestamp": "2025-06-21T13:00:00",
    "status": "success"
  },
  ...
]
```

**Error Response**
```json
{
  "error": "Product not found"
}
```

---

## ⚙️ Notes

- `product_key` can be either a numeric `id` or a string `name`.
- Time format: ISO 8601 (e.g., `2025-06-30T18:00:00`).
- All times are handled in UTC.
- You can embed `bids` inside the `products` document for quick access and store all bids in a separate `bids` collection for audit trails.

---

## 📌 Deployment

**Hosted on:**  
[Railway](https://voiceagentomnidim-production.up.railway.app/)
