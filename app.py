from flask import Flask, jsonify, request, Response
from flask_mysqldb import MySQL
import jwt
import dicttoxml
from datetime import datetime, timedelta
from functools import wraps


app = Flask(__name__)


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'  
app.config['MYSQL_DB'] = 'maid_cafe'
app.config['SECRET_KEY'] = 'maid-cafe-secret-key-12345'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  

mysql = MySQL(app)


DEMO_USER = {'username': 'admin', 'password': 'password'}

# ========== JWT AUTHENTICATION DECORATOR ==========
def token_required(f):
    """Protect routes with JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        
        token = request.args.get('token')
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
        try:
           
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        
        return f(*args, **kwargs)
    return decorated

# ========== XML/JSON RESPONSE FORMATTER ==========
def format_response(data, status_code=200):
    """
    Return response in JSON or XML based on 'format' query parameter
    Example: /customers?format=xml  or  /customers?format=json
    """
    fmt = request.args.get('format', 'json').lower()
    
    if fmt == 'xml':
        
        xml = dicttoxml.dicttoxml(
            data, 
            custom_root='response', 
            attr_type=False,  
            root=True
        )
        return Response(
            xml, 
            status=status_code, 
            mimetype='application/xml',
            headers={'Content-Type': 'application/xml'}
        )
    
    
    return jsonify(data), status_code

# ========== AUTHENTICATION ENDPOINTS ==========
@app.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token
    POST /login with JSON: {"username": "admin", "password": "password"}
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    
    if username == DEMO_USER['username'] and password == DEMO_USER['password']:

        token = jwt.encode({
            'user': username,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': username
        }), 200
    
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/auth-test', methods=['GET'])
@token_required
def auth_test():
    """Test endpoint to verify JWT is working"""
    return jsonify({'message': 'JWT authentication successful!'})

# ========== CUSTOMER CRUD ENDPOINTS ==========
@app.route('/customers', methods=['GET'])
@token_required
def get_customers():
    """
    Get all customers with optional search
    GET /customers?token=YOUR_TOKEN
    GET /customers?token=YOUR_TOKEN&q=search_term
    GET /customers?token=YOUR_TOKEN&format=xml
    """
    cur = mysql.connection.cursor()
    
   
    search_term = request.args.get('q')
    
    if search_term:
        
        cur.execute("""
            SELECT * FROM customer 
            WHERE name LIKE %s 
            OR email LIKE %s 
            OR phone_number LIKE %s
        """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
    else:
        cur.execute("SELECT * FROM customer")
    
    customers = cur.fetchall()
    cur.close()
    
    return format_response({
        'customers': customers,
        'count': len(customers)
    })

@app.route('/customers/<int:customer_id>', methods=['GET'])
@token_required
def get_customer(customer_id):
    """Get a specific customer by ID"""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,))
    customer = cur.fetchone()
    cur.close()
    
    if not customer:
        return format_response({'error': 'Customer not found'}, 404)
    
    return format_response(customer)

@app.route('/customers', methods=['POST'])
@token_required
def create_customer():
    """Create a new customer"""
    data = request.get_json()
    
    # Input validation
    if not data:
        return format_response({'error': 'No data provided'}, 400)
    
    name = data.get('name')
    email = data.get('email', '')
    phone = data.get('phone_number', '')
    
    if not name:
        return format_response({'error': 'Name is required'}, 400)
    
    # Insert into database
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "INSERT INTO customer (name, email, phone_number) VALUES (%s, %s, %s)",
            (name, email, phone)
        )
        mysql.connection.commit()
        new_id = cur.lastrowid
        cur.close()
        
        # Return the created customer
        return get_customer(new_id)
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

@app.route('/customers/<int:customer_id>', methods=['PUT'])
@token_required
def update_customer(customer_id):
    """Update an existing customer"""
    data = request.get_json()
    
    if not data:
        return format_response({'error': 'No data provided'}, 400)
    
    cur = mysql.connection.cursor()
    
    # Check if customer exists
    cur.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,))
    existing = cur.fetchone()
    
    if not existing:
        cur.close()
        return format_response({'error': 'Customer not found'}, 404)
    
    # Get new values or keep existing ones
    name = data.get('name', existing['name'])
    email = data.get('email', existing['email'])
    phone = data.get('phone_number', existing['phone_number'])
    
    try:
        cur.execute(
            """UPDATE customer 
               SET name = %s, email = %s, phone_number = %s 
               WHERE customer_id = %s""",
            (name, email, phone, customer_id)
        )
        mysql.connection.commit()
        rows_affected = cur.rowcount
        cur.close()
        
        if rows_affected == 0:
            return format_response({'error': 'No changes made'}, 400)
        
        return get_customer(customer_id)
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

@app.route('/customers/<int:customer_id>', methods=['DELETE'])
@token_required
def delete_customer(customer_id):
    """Delete a customer"""
    cur = mysql.connection.cursor()
    
    # Check if customer exists
    cur.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,))
    existing = cur.fetchone()
    
    if not existing:
        cur.close()
        return format_response({'error': 'Customer not found'}, 404)
    
    # Check if customer has orders (foreign key constraint)
    cur.execute("SELECT COUNT(*) as order_count FROM orders WHERE customer_id = %s", (customer_id,))
    result = cur.fetchone()
    
    if result['order_count'] > 0:
        cur.close()
        return format_response(
            {'error': 'Cannot delete customer with existing orders. Delete orders first.'}, 
            400
        )
    
    try:
        cur.execute("DELETE FROM customer WHERE customer_id = %s", (customer_id,))
        mysql.connection.commit()
        rows_affected = cur.rowcount
        cur.close()
        
        if rows_affected == 0:
            return format_response({'error': 'Customer not found'}, 404)
        
        return format_response({
            'message': 'Customer deleted successfully',
            'customer_id': customer_id
        })
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

# ========== MAID CRUD ENDPOINTS ==========
@app.route('/maids', methods=['GET'])
@token_required
def get_maids():
    """Get all maids with optional search"""
    cur = mysql.connection.cursor()
    
    search_term = request.args.get('q')
    
    if search_term:
        cur.execute("SELECT * FROM maid WHERE name LIKE %s", (f"%{search_term}%",))
    else:
        cur.execute("SELECT * FROM maid")
    
    maids = cur.fetchall()
    cur.close()
    
    # Convert timedelta to string
    formatted_maids = []
    for maid in maids:
        maid_dict = dict(maid)
        # Convert time fields to string
        if maid_dict.get('shift_start_time'):
            maid_dict['shift_start_time'] = str(maid_dict['shift_start_time'])
        if maid_dict.get('shift_end_time'):
            maid_dict['shift_end_time'] = str(maid_dict['shift_end_time'])
        formatted_maids.append(maid_dict)
    
    return format_response({
        'maids': formatted_maids,
        'count': len(formatted_maids)
    })

@app.route('/maids/<int:maid_id>', methods=['GET'])
@token_required
def get_maid(maid_id):
    """Get a specific maid by ID"""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM maid WHERE maid_id = %s", (maid_id,))
    maid = cur.fetchone()
    cur.close()
    
    if not maid:
        return format_response({'error': 'Maid not found'}, 404)
    
    return format_response(maid)

@app.route('/maids', methods=['POST'])
@token_required
def create_maid():
    """Create a new maid"""
    data = request.get_json()
    
    if not data:
        return format_response({'error': 'No data provided'}, 400)
    
    name = data.get('name')
    start_time = data.get('shift_start_time', '09:00:00')
    end_time = data.get('shift_end_time', '17:00:00')
    
    if not name:
        return format_response({'error': 'Name is required'}, 400)
    
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            """INSERT INTO maid (name, shift_start_time, shift_end_time) 
               VALUES (%s, %s, %s)""",
            (name, start_time, end_time)
        )
        mysql.connection.commit()
        new_id = cur.lastrowid
        cur.close()
        
        return get_maid(new_id)
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

@app.route('/maids/<int:maid_id>', methods=['PUT'])
@token_required
def update_maid(maid_id):
    """Update an existing maid"""
    data = request.get_json()
    
    if not data:
        return format_response({'error': 'No data provided'}, 400)
    
    cur = mysql.connection.cursor()
    
    # Check if maid exists
    cur.execute("SELECT * FROM maid WHERE maid_id = %s", (maid_id,))
    existing = cur.fetchone()
    
    if not existing:
        cur.close()
        return format_response({'error': 'Maid not found'}, 404)
    
    # Get new values
    name = data.get('name', existing['name'])
    start_time = data.get('shift_start_time', existing['shift_start_time'])
    end_time = data.get('shift_end_time', existing['shift_end_time'])
    
    try:
        cur.execute(
            """UPDATE maid 
               SET name = %s, shift_start_time = %s, shift_end_time = %s 
               WHERE maid_id = %s""",
            (name, start_time, end_time, maid_id)
        )
        mysql.connection.commit()
        cur.close()
        
        return get_maid(maid_id)
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

@app.route('/maids/<int:maid_id>', methods=['DELETE'])
@token_required
def delete_maid(maid_id):
    """Delete a maid"""
    cur = mysql.connection.cursor()
    
    # Check if maid exists
    cur.execute("SELECT * FROM maid WHERE maid_id = %s", (maid_id,))
    existing = cur.fetchone()
    
    if not existing:
        cur.close()
        return format_response({'error': 'Maid not found'}, 404)
    
    # Check if maid has orders
    cur.execute("SELECT COUNT(*) as order_count FROM orders WHERE maid_id = %s", (maid_id,))
    result = cur.fetchone()
    
    if result['order_count'] > 0:
        cur.close()
        return format_response(
            {'error': 'Cannot delete maid with existing orders. Delete orders first.'}, 
            400
        )
    
    try:
        cur.execute("DELETE FROM maid WHERE maid_id = %s", (maid_id,))
        mysql.connection.commit()
        cur.close()
        
        return format_response({
            'message': 'Maid deleted successfully',
            'maid_id': maid_id
        })
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

# ========== ORDER CRUD ENDPOINTS ==========
@app.route('/orders', methods=['GET'])
@token_required
def get_orders():
    """
    Get all orders with advanced filtering
    Supports: customer_id, maid_id, start_date, end_date, min_amount, max_amount
    """
    cur = mysql.connection.cursor()
    
    # Get filter parameters
    customer_id = request.args.get('customer_id')
    maid_id = request.args.get('maid_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_amount = request.args.get('min_amount')
    max_amount = request.args.get('max_amount')
    
    # Build dynamic query
    query = "SELECT * FROM orders WHERE 1=1"
    params = []
    
    if customer_id:
        query += " AND customer_id = %s"
        params.append(customer_id)
    
    if maid_id:
        query += " AND maid_id = %s"
        params.append(maid_id)
    
    if start_date:
        query += " AND order_date >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND order_date <= %s"
        params.append(end_date)
    
    if min_amount:
        query += " AND total_amount >= %s"
        params.append(float(min_amount))
    
    if max_amount:
        query += " AND total_amount <= %s"
        params.append(float(max_amount))
    
    # Execute query
    cur.execute(query, tuple(params) if params else ())
    orders = cur.fetchall()
    cur.close()
    
    return format_response({
        'orders': orders,
        'count': len(orders)
    })

@app.route('/orders/<int:order_id>', methods=['GET'])
@token_required
def get_order(order_id):
    """Get a specific order by ID"""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cur.fetchone()
    cur.close()
    
    if not order:
        return format_response({'error': 'Order not found'}, 404)
    
    return format_response(order)

@app.route('/orders', methods=['POST'])
@token_required
def create_order():
    """Create a new order"""
    data = request.get_json()
    
    if not data:
        return format_response({'error': 'No data provided'}, 400)
    
    customer_id = data.get('customer_id')
    maid_id = data.get('maid_id')
    total_amount = data.get('total_amount', 0.0)
    
    # Validate required fields
    if not customer_id or not maid_id:
        return format_response(
            {'error': 'Both customer_id and maid_id are required'}, 
            400
        )
    
    cur = mysql.connection.cursor()
    
    # Verify customer exists
    cur.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,))
    if not cur.fetchone():
        cur.close()
        return format_response({'error': 'Customer not found'}, 404)
    
    # Verify maid exists
    cur.execute("SELECT * FROM maid WHERE maid_id = %s", (maid_id,))
    if not cur.fetchone():
        cur.close()
        return format_response({'error': 'Maid not found'}, 404)
    
    try:
        cur.execute(
            """INSERT INTO orders (customer_id, maid_id, total_amount) 
               VALUES (%s, %s, %s)""",
            (customer_id, maid_id, total_amount)
        )
        mysql.connection.commit()
        new_id = cur.lastrowid
        cur.close()
        
        return get_order(new_id)
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

@app.route('/orders/<int:order_id>', methods=['PUT'])
@token_required
def update_order(order_id):
    """Update an existing order"""
    data = request.get_json()
    
    if not data:
        return format_response({'error': 'No data provided'}, 400)
    
    cur = mysql.connection.cursor()
    
    # Check if order exists
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    existing = cur.fetchone()
    
    if not existing:
        cur.close()
        return format_response({'error': 'Order not found'}, 404)
    
    # Validate foreign keys if provided
    if 'customer_id' in data:
        cur.execute("SELECT * FROM customer WHERE customer_id = %s", (data['customer_id'],))
        if not cur.fetchone():
            cur.close()
            return format_response({'error': 'Customer not found'}, 404)
    
    if 'maid_id' in data:
        cur.execute("SELECT * FROM maid WHERE maid_id = %s", (data['maid_id'],))
        if not cur.fetchone():
            cur.close()
            return format_response({'error': 'Maid not found'}, 404)
    
    # Get new values
    customer_id = data.get('customer_id', existing['customer_id'])
    maid_id = data.get('maid_id', existing['maid_id'])
    total_amount = data.get('total_amount', existing['total_amount'])
    
    try:
        cur.execute(
            """UPDATE orders 
               SET customer_id = %s, maid_id = %s, total_amount = %s 
               WHERE order_id = %s""",
            (customer_id, maid_id, total_amount, order_id)
        )
        mysql.connection.commit()
        cur.close()
        
        return get_order(order_id)
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

@app.route('/orders/<int:order_id>', methods=['DELETE'])
@token_required
def delete_order(order_id):
    """Delete an order"""
    cur = mysql.connection.cursor()
    
    # Check if order exists
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    existing = cur.fetchone()
    
    if not existing:
        cur.close()
        return format_response({'error': 'Order not found'}, 404)
    
    try:
        cur.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
        mysql.connection.commit()
        cur.close()
        
        return format_response({
            'message': 'Order deleted successfully',
            'order_id': order_id
        })
        
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return format_response({'error': f'Database error: {str(e)}'}, 500)

# ========== HEALTH & INFO ENDPOINTS ==========
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1")
        cur.close()
        db_status = 'connected'
    except:
        db_status = 'disconnected'
    
    return jsonify({
        'status': 'healthy',
        'service': 'Maid Cafe REST API',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api-info', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'Maid Cafe REST API',
        'version': '1.0.0',
        'description': 'CRUD API for managing maid cafe operations',
        'author': 'Your Name',
        'features': [
            'JWT Authentication',
            'CRUD operations for Customers, Maids, Orders',
            'XML/JSON output formatting',
            'Search functionality',
            'Input validation',
            'Error handling'
        ],
        'authentication': 'Use /login endpoint to get JWT token',
        'output_format': 'Add ?format=xml for XML, or ?format=json for JSON (default)'
    })

# ========== ERROR HANDLERS ==========
@app.errorhandler(404)
def not_found(error):
    return format_response({'error': 'Resource not found'}, 404)

@app.errorhandler(500)
def internal_error(error):
    return format_response({'error': 'Internal server error'}, 500)

@app.errorhandler(400)
def bad_request(error):
    return format_response({'error': 'Bad request'}, 400)

# ========== RUN APPLICATION ==========
if __name__ == '__main__':
    print("=" * 50)
    print("Maid Cafe REST API")
    print("Starting on http://localhost:5000")
    print("Endpoints:")
    print("  POST /login           - Get JWT token")
    print("  GET  /customers       - List customers")
    print("  GET  /maids           - List maids")
    print("  GET  /orders          - List orders")
    print("  GET  /health          - Health check")
    print("  GET  /api-info        - API information")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)