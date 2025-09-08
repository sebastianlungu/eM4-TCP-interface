# Wallbox eM4 EVSE Modbus TCP Controller

Production-ready Python controller for monitoring and managing Wallbox eM4 electric vehicle charging stations over Modbus TCP.

## Features

- 📊 **Real-time monitoring**: Read charging status, currents, voltages, power, and energy
- ⚡ **Current control**: Set maximum charging current (Icmax) with safety validation
- 🖥️ **Interactive interface**: User-friendly menu-driven interface
- 📟 **Command line**: Direct CLI commands for automation
- 🔧 **Multi-outlet support**: Control multiple charging outlets
- 🛡️ **Safety validation**: Respects installation limits and device constraints

## Quick Start

### 1. Install Dependencies

**Windows:**
```bash
install.bat
```

**Linux/macOS:**
```bash
./install.sh
```

**Manual installation:**
```bash
pip install -r requirements.txt
```

### 2. Configure Your eM4

Edit `config.py` and set your eM4's IP address:
```python
EM4_IP = "192.168.1.157"  # Your eM4 IP address
```

### 3. Run the Interface

**Interactive menu (recommended):**
```bash
python em4_interface.py
```

**Command line:**
```bash
# Read all metrics
python em4_modbus.py read

# Set maximum current to 16A
python em4_modbus.py set-icmax 16

# Help
python em4_modbus.py --help
```

## Requirements

- **Python**: 3.7 or higher
- **pymodbus**: 3.6.x (automatically installed by setup scripts)
- **Network**: eM4 must be accessible via TCP/IP

## Configuration

All settings are in `config.py`:

```python
# Network settings
EM4_IP = "192.168.1.157"    # Your eM4 IP address
EM4_PORT = 502              # Modbus TCP port
EM4_UNIT_ID = 0xFF          # Unit identifier

# Current limits
MIN_CURRENT = 6.0           # Minimum current (A)
MAX_CURRENT = 32.0          # Maximum current (A)

# Display settings
DEFAULT_OUTLET = 1          # Default outlet number
```

## Usage Examples

### Interactive Interface

```
============================================================
           Wallbox eM4 EVSE Control Interface
============================================================
📡 Connected to: 192.168.1.157:502
⚡ Current outlet: 1

Available Commands:
1. 📊 Read Current Status & Metrics
2. ⚡ Set Maximum Current (Icmax)
3. 🔌 Change Outlet Number
4. 🌐 Change IP Address
5. 🔄 Reconnect to Device
6. ❓ Show Help
0. 🚪 Exit
```

### Command Line Interface

```bash
# Read metrics with default settings
python em4_modbus.py read

# Read specific outlet
python em4_modbus.py --outlet 2 read

# Set current limit
python em4_modbus.py set-icmax 20

# Override IP address
python em4_modbus.py --ip 192.168.1.100 read
```

### Sample Output

```
Outlet 1  | Status: Charging (0x00C2)
Ic / Icmax / Idefault / Irated: 16.0 A / 20.0 A / 25.0 A / 32.0 A
Phase I [A]: L1=15.8  L2=0.0  L3=0.0
Phase U [V]: L1=231.4 L2=0.0 L3=0.0
Active Power: 3.55 kW
Energy: 12.34 kWh
```

## Understanding the Metrics

| Metric | Description |
|--------|-------------|
| **Ic** | Current being delivered to EV |
| **Icmax** | Your maximum current setting (adjustable) |
| **Idefault** | Installation/safety limit (fixed) |
| **Irated** | Device maximum capacity (fixed) |
| **Status** | Charging state (Ready, Charging, Error, etc.) |
| **Phase I/U** | Per-phase current and voltage |
| **Active Power** | Current power consumption (kW) |
| **Energy** | Total energy delivered (kWh) |

## Safety Notes

- **Current limits**: Icmax cannot exceed Idefault (installation limit)
- **Minimum current**: 6A minimum for safe EV charging
- **Installation**: Must respect local electrical codes and eM4 installation manual
- **Network security**: Secure your network connection to the eM4

## Troubleshooting

### Connection Issues

```
❌ Connection failed: [Errno 111] Connection refused
```
- Check IP address in config.py
- Verify eM4 is powered and network accessible
- Check firewall settings
- Ensure Modbus TCP is enabled on eM4

### Permission Denied
```
❌ Error setting Icmax: Requested 25A exceeds installation limit 20A
```
- Current setting exceeds installation limit (Idefault)
- Reduce requested current or check installation configuration

### Import Errors
```
Error: pymodbus not found
```
- Run the installation script: `install.bat` (Windows) or `./install.sh` (Linux/macOS)
- Or manually: `pip install -r requirements.txt`

## File Structure

```
eM4-TCP/
├── em4_modbus.py      # Core Modbus TCP client
├── em4_interface.py   # Interactive menu interface
├── config.py          # Configuration settings
├── requirements.txt   # Python dependencies
├── install.bat        # Windows installation script
├── install.sh         # Linux/macOS installation script
└── README.md          # This file
```

## Technical Details

- **Protocol**: Modbus TCP (Function codes 0x03 read, 0x10 write)
- **Port**: 502 (standard Modbus TCP)
- **Unit ID**: 0xFF (eM4 standard)
- **Register format**: Big-endian for multi-register values
- **Timeout**: 3 seconds with automatic retry

## License

This project is designed for use with Wallbox eM4 EVSE systems. Ensure compliance with local electrical codes and safety regulations.