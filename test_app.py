"""
Unit tests for Maid Cafe REST API
Run with: python -m pytest test_app.py -v
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import jwt
from datetime import datetime, timedelta
from app import app, DEMO_USER, format_response 

class TestMaidCafeAPI(unittest.TestCase):
    
    def setUp(self):
        # Configure test app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-123'
        self.app = app.test_client()
        
        # Create a valid test token
        self.valid_token = jwt.encode({
            'user': 'admin',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
    
    # ========== AUTHENTICATION TESTS ==========
    # (Existing tests kept as-is, all good)
    
    def test_login_success(self):
        """Test successful login returns JWT token"""
        response = self.app.post('/login', 
                                 json={'username': 'admin', 'password': 'password'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('token', data)
    
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = self.app.post('/login', 
                                 json={'username': 'admin', 'password': 'wrong'})
        self.assertEqual(response.status_code, 401)
    
    def test_login_empty_json(self):
        """Test login with empty JSON"""
        response = self.app.post('/login', json={})
        self.assertEqual(response.status_code, 400)
    
    def test_auth_test_endpoint_without_token(self):
        """Test protected endpoint without token"""
        response = self.app.get('/auth-test')
        self.assertEqual(response.status_code, 401)
    
    def test_auth_test_endpoint_with_valid_token(self):
        """Test protected endpoint with valid token"""
        response = self.app.get(f'/auth-test?token={self.valid_token}')
        self.assertEqual(response.status_code, 200)
    
    # ========== FORMATTING TESTS (New) ==========

    @patch('app.mysql')
    def test_get_customers_xml_format(self, mock_mysql):
        """Test GET /customers returns XML format when requested"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'customer_id': 1, 'name': 'Aying', 'email': 'a@example.com'}
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.get(f'/customers?token={self.valid_token}&format=xml')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'application/xml', response.headers.get('Content-Type').lower().encode())
        self.assertIn(b'<name>Aying</name>', response.data)

    # ========== CUSTOMER CRUD TESTS ==========
    
    @patch('app.mysql')
    def test_get_customers_success(self, mock_mysql):
        """Test GET /customers returns customer list"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'customer_id': 1, 'name': 'Aying'}]
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.get(f'/customers?token={self.valid_token}')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['customers']), 1)
    
    @patch('app.mysql')
    def test_create_customer_success(self, mock_mysql):
        """Test POST /customers creates new customer"""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 3
        # Mock fetchone to return the newly created customer after POST (called by get_customer)
        mock_cursor.fetchone.return_value = {'customer_id': 3, 'name': 'New Customer', 'email': ''}
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        customer_data = {'name': 'New Customer'}
        response = self.app.post(f'/customers?token={self.valid_token}', json=customer_data)
        
        self.assertEqual(response.status_code, 200) 
        mock_mysql.connection.commit.assert_called()

    @patch('app.mysql')
    def test_update_customer_not_found(self, mock_mysql):
        """Test PUT /customers/<id> with non-existent ID (Edge Case 404)"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None 
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.put(f'/customers/999?token={self.valid_token}',
                                 json={'name': 'Ghost Name'})
        
        self.assertEqual(response.status_code, 404)
    
    @patch('app.mysql')
    def test_delete_customer_not_found(self, mock_mysql):
        """Test DELETE /customers/<id> with non-existent ID (Edge Case 404)"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None 
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.delete(f'/customers/999?token={self.valid_token}')
        
        self.assertEqual(response.status_code, 404)

    @patch('app.mysql')
    def test_delete_customer_with_orders(self, mock_mysql):
        """Test DELETE /customers/<id> when customer has orders (Edge Case 400)"""
        mock_cursor = MagicMock()
        
        mock_cursor.fetchone.side_effect = [
            {'customer_id': 1}, 
            {'order_count': 3} 
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.delete(f'/customers/1?token={self.valid_token}')
        
        self.assertEqual(response.status_code, 400)
    
    # ========== MAID CRUD TESTS ==========
    
    @patch('app.mysql')
    def test_get_maids_search(self, mock_mysql):
        """Test GET /maids with search functionality"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'maid_id': 1, 'name': 'Lucy', 'shift_start_time': '09:00:00', 'shift_end_time': '17:00:00'}
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.get(f'/maids?token={self.valid_token}&q=Lucy')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['maids']), 1)
        # Verify execute was called with the search term
        mock_cursor.execute.assert_called_with(
            'SELECT * FROM maid WHERE name LIKE %s', ('%Lucy%',)
        )
        
    @patch('app.mysql')
    def test_delete_maid_success(self, mock_mysql):
        """Test DELETE /maids/<id> success"""
        mock_cursor = MagicMock()
        
        mock_cursor.fetchone.side_effect = [
            {'maid_id': 1}, 
            {'order_count': 0} 
        ]
        mock_cursor.rowcount = 1 
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.delete(f'/maids/1?token={self.valid_token}')
        
        self.assertEqual(response.status_code, 200)
        mock_cursor.execute.assert_called_with("DELETE FROM maid WHERE maid_id = %s", (1,))


    # ========== ORDER CRUD TESTS (Full Coverage) ==========
    
    @patch('app.mysql')
    def test_get_orders_success(self, mock_mysql):
        """Test GET /orders returns a list of orders"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'order_id': 1, 'customer_id': 1, 'maid_id': 1, 'total_amount': 25.50}
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.get(f'/orders?token={self.valid_token}')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 1)
    
    @patch('app.mysql')
    def test_get_orders_filtering_by_amount(self, mock_mysql):
        """Test GET /orders advanced filtering by min_amount and max_amount"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'order_id': 1, 'total_amount': 50.0}
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.get(
            f'/orders?token={self.valid_token}&min_amount=40.0&max_amount=60.0'
        )
        
        self.assertEqual(response.status_code, 200)
        # Check that the dynamic query was constructed correctly
        mock_cursor.execute.assert_called_with(
            'SELECT * FROM orders WHERE 1=1 AND total_amount >= %s AND total_amount <= %s', 
            (40.0, 60.0)
        )

    @patch('app.mysql')
    def test_create_order_success(self, mock_mysql):
        """Test POST /orders creates a new order"""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 10
        
        mock_cursor.fetchone.side_effect = [
            {'customer_id': 1}, 
            {'maid_id': 1},     
            {'order_id': 10, 'customer_id': 1, 'maid_id': 1, 'total_amount': 30.0} 
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        order_data = {'customer_id': 1, 'maid_id': 1, 'total_amount': 30.0}
        response = self.app.post(f'/orders?token={self.valid_token}', json=order_data)
        
        self.assertEqual(response.status_code, 200) 
        mock_mysql.connection.commit.assert_called()

    @patch('app.mysql')
    def test_create_order_missing_fk(self, mock_mysql):
        """Test POST /orders with non-existent maid_id (Edge Case 404)"""
        mock_cursor = MagicMock()
        
        mock_cursor.fetchone.side_effect = [
            {'customer_id': 1}, 
            None 
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        order_data = {'customer_id': 1, 'maid_id': 999, 'total_amount': 10.0}
        response = self.app.post(f'/orders?token={self.valid_token}', json=order_data)
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('maid not found', data['error'].lower())
        
    @patch('app.mysql')
    def test_delete_order_success(self, mock_mysql):
        """Test DELETE /orders/<id> success"""
        mock_cursor = MagicMock()
        
        mock_cursor.fetchone.return_value = {'order_id': 5}
        mock_cursor.rowcount = 1 
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.delete(f'/orders/5?token={self.valid_token}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Order deleted successfully')


    # ========== UTILITY TESTS (New) ==========
    
    @patch('app.mysql')
    def test_health_check_success(self, mock_mysql):
        """Test GET /health check (connected status)"""
        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor
        
        response = self.app.get('/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'connected')

    @patch('app.mysql', side_effect=Exception('DB Down'))
    def test_health_check_db_disconnected(self, mock_mysql):
        """Test GET /health check (disconnected status)"""
        response = self.app.get('/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'disconnected')

if __name__ == '__main__':
    unittest.main()