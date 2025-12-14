# CSE_Project# Maid Cafe REST API

A secure, token-authenticated RESTful API built with **Flask** and **PyMySQL** to manage customer, maid, and order data for a themed cafe. This project demonstrates all core CRUD operations, advanced query filtering, database error handling, and unit testing using Python.


This project was built to meet the following core requirements:

* **Full CRUD (Create, Read, Update, Delete)** implemented for **Customers**, **Maids**, and **Orders**.
* **Token-based Authentication (JWT)** implemented for all critical endpoints.
* **Advanced Query Filtering** on collection endpoints (e.g., searching customers by name, filtering orders by total amount).
* **Data Formatting** support, allowing users to request data in either **JSON** (default) or **XML** format.

### 🛡️ Robust Error Handling

The API includes specific logic to manage and return appropriate HTTP status codes for robust client interaction:

* **401 Unauthorized** for missing or invalid tokens.
* **404 Not Found** for requests to non-existent resources (e.g., fetching an order that was deleted).
* **400 Bad Request** for Foreign Key violations (critical demonstration: preventing the deletion of a customer who has existing orders).

## 🧪 Unit Testing and Quality Assurance

The project includes a comprehensive test suite in `test_app.py` using Python's standard `unittest` framework, along with mocking for database calls.

### Running Tests

1.  Ensure your virtual environment is active.
2.  Execute the following command:
    ```bash
    python -m pytest test_app.py -v
    ```

### Prerequisites

* Python 3.x
* MySQL Server (with a running instance)

### Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone [YOUR_GITHUB_REPO_HTTPS_URL]
    cd maid_cafe_api
    ```
2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Database Configuration:**
    * Update the MySQL connection details (user, password, host, database name) in the `app.py` file to match your local MySQL server setup.
    * Run your provided SQL schema file to create the necessary `customer`, `maid`, and `orders` tables.
5.  **Run the API:**
    ```bash
    python app.py
    ```

## 📚 API Endpoints Summary

| Method | Endpoint | Description | Authentication |
| :--- | :--- | :--- | :--- |
| `POST` | `/login` | Generates a JWT token required for all protected routes. | Public |
| `GET` | `/customers` | Retrieve all customers. Supports `?q=<search_term>` and `?format=xml`. | Token Required |
| `POST` | `/customers` | Creates a new customer. | Token Required |
| `PUT` | `/customers/<id>` | Updates a customer's details. | Token Required |
| `DELETE` | `/customers/<id>` | Deletes a customer. | Token Required |
| `GET` | `/orders` | Retrieve all orders. Supports `?min_amount=` and `&max_amount=` filtering. | Token Required |
| `GET` | `/health` | Simple check for API status and database connection. | Public |

## 💡 Demonstration Script (PowerShell)

The following sequence of commands was used to successfully demonstrate all CRUD operations and error handling in the environment.

1.  **Login & Token Assignment:**
    `$token = (Invoke-RestMethod http://localhost:5000/login -Method Post -Body '{"username":"admin","password":"password"}' -ContentType 'application/json').token`
2.  **Create (POST) and Assign ID (Manual Step):**
    `Invoke-RestMethod -Uri "http://localhost:5000/customers?token=$token" -Method POST -Body '{"name": "Demo Customer", "email": "demo@cafe.com"}'`
    *Manually assign the returned ID:* `$new_id = [the returned customer_id]`
3.  **Read (GET) by ID:**
    `Invoke-RestMethod -Uri "http://localhost:5000/customers/$($new_id)?token=$token"`
4.  **Update (PUT):**
    `Invoke-RestMethod -Uri "http://localhost:5000/customers/$($new_id)?token=$token" -Method PUT -Body '{"name": "UPDATED DEMO NAME"}'`
5.  **Foreign Key Error Demonstration (400):**
    *Tries to delete customer 1 (who has orders) and expects a 400 Bad Request.*
    `Invoke-RestMethod -Uri "http://localhost:5000/customers/1?token=$token" -Method DELETE`
6.  **Successful Delete (D):**
    `Invoke-RestMethod -Uri "http://localhost:5000/customers/$($new_id)?token=$token" -Method DELETE`

## 👤 Author

* [John Carlo Dagoy]