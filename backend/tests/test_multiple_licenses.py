"""
Test script to generate multiple license keys for different customers
using the SAME key pair (to demonstrate the system)
"""
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generate_license import create_license

# Generate licenses for two different customers
print("=" * 60)
print("GENERATING TEST LICENSES")
print("=" * 60)
print()

# Customer 1: jeduapf (30 days)
print("📧 Customer: jeduapf")
print("⏰ Validity: 30 days")
token1 = create_license("jeduapf", 30)
print("🔑 License Key:")
print(token1)
print()
print("-" * 60)
print()

# Customer 2: jeduapff (60 days)
print("📧 Customer: jeduapff")
print("⏰ Validity: 60 days")
token2 = create_license("jeduapff", 60)
print("🔑 License Key:")
print(token2)
print()
print("=" * 60)
print()

print("✅ Both licenses created using the SAME key pair!")
print("📌 Copy each token to test in your app")
print()
print("To test:")
print("1. Delete the container's .license_data:")
print("   docker exec zeco-backend-1 rm -f .license_data")
print("2. Navigate to http://localhost:5173")
print("3. Paste token and activate")
print("4. Repeat with the other token")
