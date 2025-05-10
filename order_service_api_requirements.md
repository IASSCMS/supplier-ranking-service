# Order Service API Requirements

The Supplier Ranking Service requires the following 4 API endpoints from the Order Service. Please implement these endpoints to enable proper communication between our services.

## 1. Get Supplier Transactions

**Endpoint:** `GET /api/v1/transactions/`

**Parameters:**
- `supplier_id` (required): ID of the supplier
- `start_date` (optional): ISO formatted date string for filtering transactions
- `status` (optional): Comma-separated list of status values to filter by
- `has_delivery_date` (optional): Boolean indicating if only transactions with delivery dates should be returned

**Expected Response Format:**
```json
[
  {
    "id": 12345,
    "supplier_id": 101,
    "order_id": "ORD-789",
    "created_at": "2025-05-01T14:30:00Z",
    "status": "completed",
    "amount": 5250.00,
    "currency": "USD",
    "expected_delivery_date": "2025-05-10T00:00:00Z",
    "actual_delivery_date": "2025-05-09T14:20:00Z",
    "items": [
      {
        "product_id": "PROD-123",
        "quantity": 10,
        "unit_price": 525.00
      }
    ]
  }
]
```

## 2. Get Supplier Performance Records

**Endpoint:** `GET /api/v1/supplier-performance/`

**Parameters:**
- `supplier_id` (required): ID of the supplier
- `start_date` (optional): ISO formatted date string for filtering records

**Expected Response Format:**
```json
[
  {
    "date": "2025-05-01T00:00:00Z",
    "supplier_id": 101,
    "quality_score": 8.5,
    "defect_rate": 1.5,
    "return_rate": 0.8,
    "on_time_delivery_rate": 97.2,
    "price_competitiveness": 8.0,
    "responsiveness": 8.5,
    "fill_rate": 98.5,
    "order_accuracy": 99.1
  }
]
```

## 3. Get Supplier Aggregated Performance

**Endpoint:** `GET /api/v1/supplier-performance/aggregated/{supplier_id}`

**Parameters:**
- `supplier_id` (in path): ID of the supplier
- `start_date` (optional): ISO formatted date string for filtering data

**Expected Response Format:**
```json
{
  "supplier_id": 101,
  "quality_score": 8.0,
  "defect_rate": 2.0,
  "return_rate": 1.0,
  "on_time_delivery_rate": 95.0,
  "price_competitiveness": 7.5,
  "responsiveness": 8.0,
  "fill_rate": 97.0,
  "order_accuracy": 98.0
}
```

## 4. Get Supplier Category Performance

**Endpoint:** `GET /api/v1/supplier-category-performance/{supplier_id}`

**Parameters:**
- `supplier_id` (in path): ID of the supplier

**Expected Response Format:**
```json
{
  "supplier_id": 101,
  "categories": [
    {
      "category_id": "CAT-1",
      "category_name": "Electronics",
      "quality_score": 8.7,
      "defect_rate": 1.2,
      "return_rate": 0.7,
      "on_time_delivery_rate": 98.1,
      "price_competitiveness": 8.2,
      "responsiveness": 8.6
    },
    {
      "category_id": "CAT-2",
      "category_name": "Office Supplies",
      "quality_score": 9.1,
      "defect_rate": 0.8,
      "return_rate": 0.5,
      "on_time_delivery_rate": 99.3,
      "price_competitiveness": 8.5,
      "responsiveness": 9.0
    }
  ]
}
```

## Implementation Notes

1. All endpoints should return `200 OK` with the JSON response body on success
2. Error responses should follow standard HTTP status codes:
   - `400 Bad Request` for invalid parameters
   - `404 Not Found` for non-existent resources
   - `500 Internal Server Error` for server-side issues

3. All endpoints should require proper authentication using API keys:
   - Validate the API key provided in the `Authorization` header
   - Return `401 Unauthorized` if the API key is invalid or missing

4. Implementation deadline: [Insert your required deadline]

5. Contact [Your Name/Email] for any questions or clarifications about these requirements

---

**Notes regarding Port Configuration for Local Development:**
- The Order Service should run on port 8002
- The Ranking Service will run on port 8001
- The Auth Service will run on port 8000 