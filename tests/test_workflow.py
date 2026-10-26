import database
from blockchain import Blockchain
import hashlib

def calculate_certificate_hash(name, course, org, date):
    cert_string = f"Name:{name}|Course:{course}|Org:{org}|Date:{date}"
    return hashlib.sha256(cert_string.encode()).hexdigest()

def test_full_workflow():
    print("Starting Full Project Logic Test...")

    # Setup
    database.init_db()
    database.delete_all_certificates()
    bc = Blockchain()
    bc.initialize_new_chain()

    # 1. Test Issuance
    name, course, org, date = "Koushik", "Data Science", "University X", "2026-10-22"
    cert_id = "CERT-TEST-001"
    cert_hash = calculate_certificate_hash(name, course, org, date)

    database.save_certificate(cert_id, name, course, org, date, cert_hash)
    bc.add_block(f"ID:{cert_id} | Hash:{cert_hash}")
    print("✅ Issuance Successful")

    # 2. Test Verification (Should pass)
    cert = database.get_certificate(cert_id)
    recalculated_hash = calculate_certificate_hash(cert['student_name'], cert['course_name'], cert['organization'], cert['issue_date'])

    is_valid, _ = bc.is_chain_valid()
    if recalculated_hash == cert['certificate_hash'] and is_valid:
        print("✅ Verification Successful")
    else:
        print("❌ Verification Failed Unexpectedly")
        return

    # 3. Test Tampering (Modify DB)
    database.update_certificate_data(cert_id, "Hacker")
    print("Simulating Tampering...")

    # 4. Test Verification after Tampering (Should fail)
    cert_tampered = database.get_certificate(cert_id)
    recalculated_hash_tampered = calculate_certificate_hash(cert_tampered['student_name'], cert_tampered['course_name'], cert_tampered['organization'], cert_tampered['issue_date'])

    if recalculated_hash_tampered != cert_tampered['certificate_hash']:
        print("✅ Tampering Detected Successfully!")
    else:
        print("❌ Failed to detect tampering!")

if __name__ == "__main__":
    test_full_workflow()
