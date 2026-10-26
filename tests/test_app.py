import unittest
import os
import sys
import hashlib
import sqlite3
from flask import url_for

# Add project root to sys.path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, calculate_certificate_hash
import database
from blockchain import Blockchain

class CertChainTestCase(unittest.TestCase):

    def setUp(self):
        """Set up a clean state for every test."""
        # Configure Flask for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        # Use in-memory database for tests to avoid Disk I/O errors in VM
        database.set_db_path(':memory:')
        database.init_db()
        database.delete_all_certificates()
        self.bc = Blockchain()
        self.bc.initialize_new_chain()

    def test_routes(self):
        """Test that all major pages load correctly."""
        # Root route should redirect to landing
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/landing', response.location)

        routes = ['/landing', '/dashboard', '/issue', '/verify', '/explorer', '/architecture']
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed to load")

    def test_issuance_and_verification_success(self):
        """Test the full happy path: Issue -> Verify."""
        # 1. Issue Certificate
        data = {
            'student_name': 'Test User',
            'course_name': 'Blockchain 101',
            'organization': 'Cert University',
            'issue_date': '2026-10-22'
        }
        response = self.client.post('/issue', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Success! Certificate issued", response.data)

        # Extract Cert ID from response
        # Response is bytes, we need to find the ID which is something like CERT-XXXXXX
        import re
        match = re.search(b"ID: (CERT-[A-Z0-9]+)", response.data)
        self.assertTrue(match, "Could not find Certificate ID in response")
        cert_id = match.group(1).decode()

        # 2. Verify Certificate
        verify_response = self.client.post('/verify', data={'cert_id': cert_id}, follow_redirects=True)
        self.assertEqual(verify_response.status_code, 200)
        self.assertIn(b"Verified", verify_response.data)
        self.assertIn(b"authentic and verified", verify_response.data)

    def test_unknown_certificate_id(self):
        """Test that invalid IDs are handled gracefully."""
        response = self.client.post('/verify', data={'cert_id': 'CERT-NONEXISTENT'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Not Found", response.data)
        self.assertIn(b"No such record exists", response.data)

    def test_certificate_data_tampering(self):
        """Test that modifying data in the DB is detected by the blockchain."""
        # 1. Issue a valid certificate
        name, course, org, date = "Tamper Test", "Security", "Uni X", "2026-10-22"
        cert_id = "CERT-TAMPER-01"
        cert_hash = calculate_certificate_hash(name, course, org, date)
        database.save_certificate(cert_id, name, course, org, date, cert_hash)
        self.bc.add_block(f"ID:{cert_id} | Hash:{cert_hash}")

        # 2. Simulate attack: Modify name in DB
        database.update_certificate_data(cert_id, "Evil Hacker")

        # 3. Verify
        response = self.client.post('/verify', data={'cert_id': cert_id}, follow_redirects=True)
        self.assertIn(b"Tampered", response.data)
        self.assertIn(b"DATABASE TAMPERING DETECTED", response.data)

    def test_blockchain_corruption(self):
        """Test that breaking a block hash invalidates the entire chain."""
        # 1. Ensure we have at least one block after genesis
        self.bc.add_block("Test Block Data")

        # 2. Corrupt the block hash
        self.bc.chain[1].hash = "corrupted_value_123"

        # 3. Check validity
        valid, msg = self.bc.is_chain_valid()
        self.assertFalse(valid)
        self.assertIn("modified", msg.lower())

    def test_safe_reset(self):
        """Test that the reset route clears data and restores a valid genesis chain."""
        # 1. Add some data
        self.client.post('/issue', data={'student_name': 'A', 'course_name': 'B', 'organization': 'C', 'issue_date': '2026-01-01'})

        # 2. Trigger reset
        response = self.client.get('/reset', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # 3. Verify state is clean
        # Only genesis block should remain
        self.assertEqual(len(self.bc.chain), 1)
        # DB should be empty
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM certificates')
        self.assertEqual(cursor.fetchone()['count'], 0)
        conn.close()

if __name__ == '__main__':
    unittest.main()
