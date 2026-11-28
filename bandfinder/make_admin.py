"""Make an existing Band Finder user an admin, from the command line.

This is how the very first admin is created. After that, admins can make
other admins from the Admin page.

1. Sign up on the website as normal.
2. Then run this from the lowcode-project folder:
       python bandfinder/make_admin.py YOUR_USERNAME
"""
import sys

import db


def main():
    if len(sys.argv) != 2:
        print("Usage: python bandfinder/make_admin.py USERNAME")
        sys.exit(1)
    username = sys.argv[1]
    user = db.get_user_by_username(username)
    if user is None:
        print("No user called '" + username + "'. Sign up on the website first.")
        sys.exit(1)
    db.make_admin(user["id"])
    print(username + " is now an admin.")


if __name__ == "__main__":
    main()
