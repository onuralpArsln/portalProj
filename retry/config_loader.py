#!/usr/bin/env python3
"""
Configuration loader for captive portal system
Reads configuration from config.sh shell script
"""

import os
import subprocess
import sys

def load_config():
    """
    Load configuration from config.sh by sourcing it in bash
    and reading the environment variables
    
    Returns:
        dict: Configuration dictionary with all settings
    """
    # Find config.sh in the directory of the executable/script (external)
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    
    config_file = os.path.join(script_dir, 'config.sh')
    
    if not os.path.exists(config_file):
        print(f"Error: config.sh not found at {config_file}")
        sys.exit(1)
    
    # Source the config.sh file and print all variables as JSON-like format
    # We use bash to source the file, then print the variables
    bash_command = f"""
    source {config_file}
    echo "INTERFACE=$INTERFACE"
    echo "STATIC_IP=$STATIC_IP"
    echo "NETMASK=$NETMASK"
    echo "DHCP_RANGE_START=$DHCP_RANGE_START"
    echo "DHCP_RANGE_END=$DHCP_RANGE_END"
    echo "SSID=$SSID"
    echo "WPA_PASSPHRASE=$WPA_PASSPHRASE"
    echo "CHANNEL=$CHANNEL"
    echo "SERVER_PORT=$SERVER_PORT"
    echo "MYSQL_USER=$MYSQL_USER"
    echo "MYSQL_PASSWORD=$MYSQL_PASSWORD"
    echo "MYSQL_DATABASE=$MYSQL_DATABASE"
    echo "USER_ID=$USER_ID"
    echo "SHOP_ID=$SHOP_ID"
    """
    
    try:
        result = subprocess.run(
            ['bash', '-c', bash_command],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output
        config = {}
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"').strip("'")
                config[key] = value
        
        return config
        
    except subprocess.CalledProcessError as e:
        print(f"Error loading config.sh: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)


def get_mysql_config(config=None):
    """
    Get MySQL configuration dictionary from config.sh
    
    Args:
        config: Optional pre-loaded config dict
        
    Returns:
        dict: MySQL connector configuration
    """
    if config is None:
        config = load_config()
    
    return {
        'user': config.get('MYSQL_USER', 'fungames'),
        'password': config.get('MYSQL_PASSWORD', ''),
        'database': config.get('MYSQL_DATABASE', 'fungames'),
        'ssl_disabled': True
    }


def get_user_id(config=None):
    """Get USER_ID from config"""
    if config is None:
        config = load_config()
    return int(config.get('USER_ID', '320'))


def get_shop_id(config=None):
    """Get SHOP_ID from config"""
    if config is None:
        config = load_config()
    return int(config.get('SHOP_ID', '1'))


if __name__ == "__main__":
    # Test the config loader
    print("Testing config loader...")
    print("=" * 60)
    
    config = load_config()
    
    print("Network Configuration:")
    print(f"  Interface:    {config.get('INTERFACE')}")
    print(f"  Static IP:    {config.get('STATIC_IP')}")
    print(f"  DHCP Range:   {config.get('DHCP_RANGE_START')} - {config.get('DHCP_RANGE_END')}")
    
    print("\nWiFi Configuration:")
    print(f"  SSID:         {config.get('SSID')}")
    print(f"  Password:     {config.get('WPA_PASSPHRASE')}")
    print(f"  Channel:      {config.get('CHANNEL')}")
    
    print("\nServer Configuration:")
    print(f"  Port:         {config.get('SERVER_PORT')}")
    
    print("\nDatabase Configuration:")
    print(f"  User:         {config.get('MYSQL_USER')}")
    print(f"  Database:     {config.get('MYSQL_DATABASE')}")
    print(f"  User ID:      {config.get('USER_ID')}")
    print(f"  Shop ID:      {config.get('SHOP_ID')}")
    
    print("\n" + "=" * 60)
    print("MySQL Config Dict:")
    print(get_mysql_config(config))
