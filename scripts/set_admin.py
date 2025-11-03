"""
Script to set admin role for a user in MongoDB.

Usage:
    python scripts/set_admin.py <clerk_user_id>
    
Or run interactively:
    python scripts/set_admin.py
"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend_api.core.config import get_settings

settings = get_settings()


async def set_admin_role(clerk_user_id: str = None):
    """Set admin role for a user."""
    mongodb_url = getattr(settings, 'mongodb_url', None)
    if not mongodb_url:
        print("❌ Error: MONGODB_URL not set in .env file")
        print("   Please add: MONGODB_URL=mongodb://localhost:27017")
        return
    
    db_name = getattr(settings, 'mongodb_database', 'equitas')
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[db_name]
    
    if not clerk_user_id:
        # Interactive mode - list users and let them choose
        print("\n📋 Finding users in database...")
        users = await db.users.find({}).to_list(length=100)
        
        if not users:
            print("❌ No users found in database.")
            print("   Please sign up through the frontend first.")
            client.close()
            return
        
        print("\nAvailable users:")
        print("-" * 80)
        for i, user in enumerate(users, 1):
            role = user.get("role", "user")
            role_badge = "👑 ADMIN" if role == "admin" else "👤 USER"
            print(f"{i}. {user.get('email', 'No email')} ({user.get('name', 'No name')})")
            print(f"   Clerk ID: {user['clerk_user_id']}")
            print(f"   Role: {role_badge}")
            print(f"   Tenant ID: {user.get('tenant_id', 'N/A')}")
            print()
        
        choice = input("Enter the number of the user to make admin (or 'q' to quit): ").strip()
        
        if choice.lower() == 'q':
            print("Cancelled.")
            client.close()
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(users):
                clerk_user_id = users[idx]['clerk_user_id']
            else:
                print("❌ Invalid selection")
                client.close()
                return
        except ValueError:
            print("❌ Invalid input")
            client.close()
            return
    
    # Update user to admin
    result = await db.users.update_one(
        {"clerk_user_id": clerk_user_id},
        {
            "$set": {
                "role": "admin",
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    if result.matched_count == 0:
        print(f"❌ User with Clerk ID '{clerk_user_id}' not found in database.")
        print("   Make sure the user has signed up through the frontend first.")
    elif result.modified_count > 0:
        user = await db.users.find_one({"clerk_user_id": clerk_user_id})
        print(f"\n✅ Success! User '{user.get('email', clerk_user_id)}' is now an admin.")
        print(f"   Clerk User ID: {clerk_user_id}")
        print(f"   Tenant ID: {user.get('tenant_id', 'N/A')}")
        print("\n   You can now access the admin dashboard at:")
        print("   http://localhost:5173/dashboard/admin")
    else:
        user = await db.users.find_one({"clerk_user_id": clerk_user_id})
        if user.get("role") == "admin":
            print(f"\n✅ User '{user.get('email', clerk_user_id)}' is already an admin.")
        else:
            print(f"\n⚠️  User found but role not updated. Current role: {user.get('role', 'user')}")
    
    client.close()


async def remove_admin_role(clerk_user_id: str):
    """Remove admin role from a user."""
    mongodb_url = getattr(settings, 'mongodb_url', None)
    if not mongodb_url:
        print("❌ Error: MONGODB_URL not set in .env file")
        return
    
    db_name = getattr(settings, 'mongodb_database', 'equitas')
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[db_name]
    
    result = await db.users.update_one(
        {"clerk_user_id": clerk_user_id},
        {
            "$set": {
                "role": "user",
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    if result.matched_count == 0:
        print(f"❌ User with Clerk ID '{clerk_user_id}' not found.")
    elif result.modified_count > 0:
        print(f"✅ Admin role removed from user '{clerk_user_id}'")
    else:
        print(f"⚠️  User '{clerk_user_id}' is not an admin.")
    
    client.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--remove":
            if len(sys.argv) > 2:
                asyncio.run(remove_admin_role(sys.argv[2]))
            else:
                print("Usage: python scripts/set_admin.py --remove <clerk_user_id>")
        else:
            asyncio.run(set_admin_role(sys.argv[1]))
    else:
        asyncio.run(set_admin_role())

