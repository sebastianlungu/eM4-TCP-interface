"""
Wallbox eM4 EVSE Configuration

Configuration settings for the eM4 Modbus TCP controller.
Modify these values to match your installation.
"""

# eM4 Device Network Settings
EM4_IP = "192.168.1.157"    # IP address of the eM4 EVSE
EM4_PORT = 502              # Modbus TCP port (standard is 502)
EM4_UNIT_ID = 0xFF          # Unit identifier for eM4 (0xFF is standard)

# Connection Settings
CONNECTION_TIMEOUT = 3.0    # Connection timeout in seconds
CONNECTION_RETRIES = 1      # Number of retry attempts

# Default Outlet Settings
DEFAULT_OUTLET = 1          # Default outlet number if not specified

# Current Limits (in Amperes)
MIN_CURRENT = 6.0          # Minimum allowed current setting
MAX_CURRENT = 32.0         # Maximum allowed current setting

# Display Settings
DECIMAL_PLACES_CURRENT = 1  # Decimal places for current display
DECIMAL_PLACES_VOLTAGE = 1  # Decimal places for voltage display  
DECIMAL_PLACES_POWER = 2    # Decimal places for power display
DECIMAL_PLACES_ENERGY = 2   # Decimal places for energy display