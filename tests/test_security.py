import unittest
import os
import sqlite3
from app import app, bc
import database
from werkzeug.security import generate_password_hash

class TestCertChainSecurity(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Use isolated test DB
        database.set_db_path(':memory:')
        database.init_db()

        # Fresh Blockchain in memory/tmp
        self.bc_file = '/tmp/security_test_blockchain.json'
        bc.storage_file = self.bc_file
        bc.initialize_new_chain()

        # Initialize test users
        self.admin_user = 'admin_test'
        self.user_pass = 'password123'
        database.create_user(self.admin_user, generate_password_hash(self.user_pass), 'admin')

        self.reg_user = 'user_test'
        database.create_user(self.reg_user, generate_password_hash(self.user_pass), 'user')

        self.disabled_user = 'disabled_test'
        database.create_user(self.disabled_user, generate_password_hash(self.user_pass), 'user')
        database.update_user_status(self.disabled_user, 0)

    def tearDown(self):
        if os.path.exists(self.bc_file):
            os.remove(self.bc_file)

    def login(self, username, password):
        return self.app.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

    def test_public_routes(self):
        """Verify that landing and architecture pages are accessible to everyone."""
        res_landing = self.app.get('/landing')
        res_arch = self.app.get('/architecture')
        self.assertEqual(res_landing.status_code, 200)
        self.assertEqual(res_arch.status_code, 200)
        self.assertEqual(self.app.get('/login').status_code, 200)

    def test_unauthenticated_access(self):
        """Verify that protected routes redirect unauthenticated users to login."""
        protected_routes = ['/dashboard', '/issue', '/verify', '/explorer', '/users', '/reset']
        for route in protected_routes:
            response = self.app.get(route)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)

    def test_valid_login(self):
        """Verify successful login for admin and user."""
        res = self.login(self.admin_user, self.user_pass)
        self.assertIn(b'Platform Overview', res.data) # Dashboard content

        self.app.get('/logout')
        res_logout = self.app.get('/dashboard')
        self.assertEqual(res_logout.status_code, 302)

    def test_invalid_login(self):
        """Verify login failure for wrong password."""
        res = self.login(self.admin_user, 'wrongpassword')
        self.assertIn(b'Invalid login credentials', res.data)

    def test_disabled_account(self):
        """Verify that disabled accounts cannot log in."""
        res = self.login(self.disabled_user, self.user_pass)
        self.assertIn(b'account is disabled', res.data)

    def test_regular_user_permissions(self):
        """Verify that regular users cannot access admin-only routes."""
        self.login(self.reg_user, self.user_pass)

        # Permitted
        self.assertEqual(self.app.get('/dashboard').status_code, 200)
        self.assertEqual(self.app.get('/issue').status_code, 200)

        # Forbidden
        self.assertEqual(self.app.get('/explorer').status_code, 403)
        self.assertEqual(self.app.get('/users').status_code, 403)

        # Direct POST to admin routes
        res_reset = self.app.post('/reset')
        self.assertEqual(res_reset.status_code, 403)

    def test_admin_permissions(self):
        """Verify that admins can access everything."""
        self.login(self.admin_user, self.user_pass)

        self.assertEqual(self.app.get('/dashboard').status_code, 200)
        self.assertEqual(self.app.get('/explorer').status_code, 200)
        self.assertEqual(self.app.get('/users').status_code, 200)

        # Test reset confirmation page
        self.assertEqual(self.app.get('/reset').status_code, 200)
        # Test actual reset
        res_reset = self.app.post('/reset')
        self.assertEqual(res_reset.status_code, 302)

    def test_regression_issuance_verification(self):
        """Ensure that issuance and verification still work after adding RBAC."""
        self.login(self.reg_user, self.user_pass)

        # Issue a cert
        self.app.post('/issue', data={
            'student_name': 'Test Student',
            'course_name': 'DS',
            'organization': 'Uni',
            'issue_date': '2026-01-01'
        })

        # Verify it exists in DB and BC
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM certificates LIMIT 1')
        cid = cursor.fetchone()['id']

        res_verify = self.app.post('/verify', data={'cert_id': cid})
        self.assertIn(b'Verified', res_verify.data)

if __name__ == '__main__':
    unittest.main()
