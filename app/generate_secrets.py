#!/usr/bin/env python3
"""
Generate secure secrets for Stock Analyst application
"""

import secrets
import string
import argparse


def generate_secret_key(length=64):
    """Generate a secure secret key for Flask"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_password(length=16):
    """Generate a secure password for database"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def main():
    parser = argparse.ArgumentParser(description='Generate secure secrets for Stock Analyst')
    parser.add_argument('--env-file', action='store_true', 
                       help='Output in .env file format')
    parser.add_argument('--docker-compose', action='store_true',
                       help='Output in docker-compose environment format')
    
    args = parser.parse_args()
    
    secret_key = generate_secret_key()
    postgres_password = generate_password()
    
    if args.env_file:
        print(f"SECRET_KEY={secret_key}")
        print(f"POSTGRES_PASSWORD={postgres_password}")
    elif args.docker_compose:
        print(f"      - SECRET_KEY={secret_key}")
        print(f"      - POSTGRES_PASSWORD={postgres_password}")
    else:
        print("🔐 Generated Secure Secrets for Stock Analyst Application")
        print("=" * 60)
        print(f"SECRET_KEY: {secret_key}")
        print(f"POSTGRES_PASSWORD: {postgres_password}")
        print()
        print("💡 Usage:")
        print("  Export these as environment variables:")
        print(f"    export SECRET_KEY='{secret_key}'")
        print(f"    export POSTGRES_PASSWORD='{postgres_password}'")
        print()
        print("  Or add to your .env file:")
        print(f"    SECRET_KEY={secret_key}")
        print(f"    POSTGRES_PASSWORD={postgres_password}")


if __name__ == "__main__":
    main()