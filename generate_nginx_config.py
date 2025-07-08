#!/usr/bin/env python3
"""
Generate nginx configuration from template
Usage: python generate_nginx_config.py [upstream_host] [upstream_port]
"""

import sys
from pathlib import Path


def generate_nginx_config(upstream_host="stockanalyst", upstream_port="5000"):
    """Generate nginx configuration from template"""
    
    print("Generating nginx configuration...")
    print(f"  Upstream host: {upstream_host}")
    print(f"  Upstream port: {upstream_port}")
    
    # Check if template exists
    template_path = Path("nginx.conf.template")
    if not template_path.exists():
        print("Error: nginx.conf.template not found")
        return False
    
    # Read template
    try:
        with open(template_path, 'r') as f:
            template_content = f.read()
    except Exception as e:
        print(f"Error reading template: {e}")
        return False
    
    # Replace variables
    config_content = template_content.replace("${UPSTREAM_HOST}", upstream_host)
    config_content = config_content.replace("${UPSTREAM_PORT}", upstream_port)
    
    # Write configuration
    try:
        with open("nginx.conf", 'w') as f:
            f.write(config_content)
    except Exception as e:
        print(f"Error writing configuration: {e}")
        return False
    
    print("nginx.conf generated successfully!")
    print(f"You can now start nginx with: nginx -c {Path.cwd()}/nginx.conf")
    return True


def main():
    """Main entry point"""
    upstream_host = sys.argv[1] if len(sys.argv) > 1 else "stockanalyst"
    upstream_port = sys.argv[2] if len(sys.argv) > 2 else "5000"
    
    success = generate_nginx_config(upstream_host, upstream_port)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()