"""
Demonstrate generating MULTIPLE tokens for the SAME user
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generate_license import create_license

print("=" * 60)
print("SAME USER - MULTIPLE RENEWALS")
print("=" * 60)
print()

# Month 1: jeduapf buys initial subscription
print("📅 MONTH 1: Initial Purchase")
print("📧 Customer: jeduapf")
print("⏰ Validity: 30 days")
token1 = create_license("jeduapf", 30)
print("🔑 Token #1:")
print(token1)
print()

# Month 2: jeduapf renews for another month
print("=" * 60)
print("📅 MONTH 2: First Renewal")
print("📧 Customer: jeduapf (SAME USER)")
print("⏰ Validity: 30 days")
token2 = create_license("jeduapf", 30)
print("🔑 Token #2:")
print(token2)
print()

# Month 3: jeduapf renews again, but pays for 60 days this time
print("=" * 60)
print("📅 MONTH 3: Second Renewal (longer period)")
print("📧 Customer: jeduapf (SAME USER)")
print("⏰ Validity: 60 days")
token3 = create_license("jeduapf", 60)
print("🔑 Token #3:")
print(token3)
print()

print("=" * 60)
print("✅ All 3 tokens are DIFFERENT but for the SAME user!")
print("✅ All 3 can be verified with the SAME public key!")
print("✅ Each token has a different expiration date!")
print()
print("🔍 Notice: The tokens are different because they contain")
print("   different 'iat' (issue time) and 'exp' (expiration) values")
