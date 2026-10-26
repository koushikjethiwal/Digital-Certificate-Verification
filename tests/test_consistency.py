import json
import unittest
import os
import sqlite3
from app import app, calculate_certificate_hash
import database
from blockchain import Blockchain

class TestBlockchainConsistency(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Use in-memory DB for tests
        database.set_db_path(':memory:')
        database.init_db()

        # Create a test user for authentication
        from werkzeug.security import generate_password_hash
        database.create_user('testuser', generate_password_hash('password'), 'user')

        # Login for all tests
        self.app.post('/login', data={'username': 'testuser', 'password': 'password'})

        # Fresh Blockchain for each test
        # We use a temporary file for BC to avoid conflicts
        self.bc_file = '/tmp/test_blockchain.json'
        self.bc = Blockchain(storage_file=self.bc_file)
        self.bc.initialize_new_chain()

        # Inject the test blockchain into the app's global bc
        import app as app_mod
        app_mod.bc = self.bc

    def tearDown(self):
        if os.path.exists(self.bc_file):
            os.remove(self.bc_file)

    def test_multiple_issuance_anchoring(self):
        """Verify that issuing multiple certificates creates matching blocks."""
        # Issue 3 certs
        for i in range(3):
            self.app.post('/issue', data={
                'student_name': f'Student {i}',
                'course_name': 'Data Science',
                'organization': 'Uni',
                'issue_date': '2026-01-01'
            })
        
        # DB should have 3, BC should have 4 (Genesis + 3)
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM certificates')
        db_count = cursor.fetchone()['count']
        
        bc_count = len(self.bc.chain)
        
        self.assertEqual(db_count, 3)
        self.assertEqual(bc_count, 4)

    def test_missing_anchor_detection(self):
        """Verify that a DB record without a block is detected as unanchored."""
        # Manually insert a record into DB WITHOUT adding to BC
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO certificates (id, student_name, course_name, organization, issue_date, certificate_hash) VALUES (?,?,?,?,?,?)',
                      ('CERT-MISSING', 'Ghost', 'Course', 'Org', '2026-01-01', 'fakehash'))
        conn.commit()

        # Dashboard check
        response = self.app.get('/dashboard')
        # We check for the warning banner text
        self.assertIn(b'Consistency Warning: Unanchored Records Detected', response.data)
        self.assertIn(b'unanchored', response.data.lower())

    def test_tampered_data_verification(self):
        """Verify that modification of DB data is caught during verification."""
        # Issue one cert
        self.app.post('/issue', data={
            'student_name': 'Original',
            'course_name': 'DS',
            'organization': 'Uni',
            'issue_date': '2026-01-01'
        })
        
        # Get the ID
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM certificates LIMIT 1')
        cid = cursor.fetchone()['id']
        
        # Tamper with the name in DB
        database.update_certificate_data(cid, 'Fraudulent')
        
        # Verify
        response = self.app.post('/verify', data={'cert_id': cid})
        self.assertIn(b'DATABASE TAMPERING DETECTED', response.data)

    def test_broken_chain_link(self):
        """Verify that a broken hash link in the blockchain is detected."""
        # Issue a cert
        self.app.post('/issue', data={
            'student_name': 'S1', 'course_name': 'C1', 'organization': 'O1', 'issue_date': '2026-01-01'
        })
        
        # Tamper with the blockchain file manually
        with open(self.bc_file, 'r') as f:
            data = json.load(f)
        
        # Corrupt the hash of Block 0
        data[0]['hash'] = 'corrupted_hash'
        
        with open(self.bc_file, 'w') as f:
            json.dump(data, f)
        
        # Reload blockchain
        self.bc.load_chain()
        
        is_valid, msg = self.bc.is_chain_valid()
        self.assertFalse(is_valid)
        self.assertIn('Block 1 is not linked', msg)

if __name__ == '__main__':
    unittest.main()
