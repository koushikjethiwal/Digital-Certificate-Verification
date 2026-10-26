import os
import sys
import hashlib
import json

# Add current directory to sys.path to allow imports of local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
from blockchain import Blockchain

def calculate_hash(name, course, org, date):
    cert_string = f"Name:{name}|Course:{course}|Org:{org}|Date:{date}"
    return hashlib.sha256(cert_string.encode()).hexdigest()

def run_tests():
    print("🚀 Starting Professional QA Test Suite...")
    print("-" * 50)

    # 1. Setup & Clean State
    database.init_db()
    database.delete_all_certificates()
    bc = Blockchain()
    bc.initialize_new_chain()

    # --- TEST 1: Happy Path ---
    print("Test 1: Valid Issuance & Verification...", end=" ")
    name, course, org, date = "Alice Smith", "B.Tech CS", "Uni A", "2026-01-01"
    cert_id = "CERT-VALID-001"
    c_hash = calculate_hash(name, course, org, date)

    database.save_certificate(cert_id, name, course, org, date, c_hash)
    bc.add_block(f"ID:{cert_id} | Hash:{c_hash}")

    cert = database.get_certificate(cert_id)
    recalc = calculate_hash(cert['student_name'], cert['course_name'], cert['organization'], cert['issue_date'])
    valid, _ = bc.is_chain_valid()

    if recalc == cert['certificate_hash'] and valid:
        print("✅ PASSED")
    else:
        print("❌ FAILED")

    # --- TEST 2: Non-Existent ID ---
    print("Test 2: Non-Existent ID handling...", end=" ")
    cert = database.get_certificate("CERT-NONE")
    if cert is None:
        print("✅ PASSED")
    else:
        print("❌ FAILED")

    # --- TEST 3: Database Tampering (The Core Feature) ---
    print("Test 3: Data Modification Detection...", end=" ")
    database.update_certificate_data(cert_id, "Evil Hacker")
    cert_t = database.get_certificate(cert_id)
    recalc_t = calculate_hash(cert_t['student_name'], cert_t['course_name'], cert_t['organization'], cert_t['issue_date'])

    if recalc_t != cert_t['certificate_hash']:
        print("✅ PASSED (Tampering Detected)")
    else:
        print("❌ FAILED (Tampering missed)")

    # --- TEST 4: Blockchain Corruption ---
    print("Test 4: Blockchain Chain Integrity...", end=" ")
    # Manually break a block hash in the chain
    bc.chain[1].hash = "corrupted_hash_123"
    valid_corrupt, _ = bc.is_chain_valid()
    if not valid_corrupt:
        print("✅ PASSED (Corruption Detected)")
    else:
        print("❌ FAILED (Corruption missed)")

    # --- TEST 5: System Reset ---
    print("Test 5: Full System Reset...", end=" ")
    database.delete_all_certificates()
    bc.initialize_new_chain()
    if len(bc.chain) == 1 and database.get_certificate(cert_id) is None:
        print("✅ PASSED")
    else:
        print("❌ FAILED")

    print("-" * 50)
    print("QA Suite Completed.")

if __name__ == "__main__":
    run_tests()
