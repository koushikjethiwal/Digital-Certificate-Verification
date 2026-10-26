import getpass
import sys
from werkzeug.security import generate_password_hash
import database

def main():
    print("--- CertChain Account Management Tool ---")
    print("Use this tool to initialize administrators and users safely.\n")

    # Ensure DB is initialized
    database.init_db()

    while True:
        print("\n1. Create New User")
        print("2. Change User Role")
        print("3. Enable/Disable User")
        print("4. List All Users")
        print("5. Exit")

        choice = input("\nSelect an option: ")

        if choice == '1':
            username = input("Enter Login ID (username): ").strip()
            if not username:
                print("Error: Username cannot be empty.")
                continue

            password = getpass.getpass("Enter Password: ")
            if not password:
                print("Error: Password cannot be empty.")
                continue

            role = input("Enter Role (user/admin) [default: user]: ").strip().lower()
            if role not in ['user', 'admin']:
                role = 'user'

            password_hash = generate_password_hash(password)
            if database.create_user(username, password_hash, role):
                print(f"Successfully created {role} account: {username}")
            else:
                print(f"Error: Username '{username}' already exists.")

        elif choice == '2':
            username = input("Enter Username to modify: ").strip()
            new_role = input("Enter New Role (user/admin): ").strip().lower()
            if new_role in ['user', 'admin']:
                database.update_user_role(username, new_role)
                print(f"Updated {username} to role: {new_role}")
            else:
                print("Error: Invalid role. Use 'user' or 'admin'.")

        elif choice == '3':
            username = input("Enter Username: ").strip()
            status = input("Set Active? (y/n): ").strip().lower()
            is_active = 1 if status == 'y' else 0
            database.update_user_status(username, is_active)
            print(f"Updated {username} active status to: {is_active}")

        elif choice == '4':
            users = database.list_users()
            print("\n--- Registered Users ---")
            print(f"{'ID':<5} {'Username':<20} {'Role':<10} {'Active':<10}")
            print("-" * 45)
            for u in users:
                active = "Yes" if u['is_active'] else "No"
                print(f"{u['id']:<5} {u['username']:<20} {u['role']:<10} {active:<10}")

        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()
