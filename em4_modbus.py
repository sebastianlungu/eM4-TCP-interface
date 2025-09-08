#!/usr/bin/env python3
"""
Wallbox eM4 EVSE Modbus TCP Controller

Production-ready script to monitor and control Wallbox eM4 charging stations
over Modbus TCP protocol.

Usage:
  python em4_modbus.py read                    # Uses config.py settings
  python em4_modbus.py --outlet 1 read         # Override outlet
  python em4_modbus.py --ip 192.168.1.50 read  # Override IP
  python em4_modbus.py set-icmax 16             # Set current limit

Requirements: pip install pymodbus>=3.0
"""

import argparse
import sys
import time
from typing import Tuple, Optional, Dict, Any

try:
    from config import (
        EM4_IP, EM4_PORT, EM4_UNIT_ID, CONNECTION_TIMEOUT, CONNECTION_RETRIES,
        DEFAULT_OUTLET, MIN_CURRENT, MAX_CURRENT,
        DECIMAL_PLACES_CURRENT, DECIMAL_PLACES_VOLTAGE, DECIMAL_PLACES_POWER, DECIMAL_PLACES_ENERGY
    )
except ImportError:
    # Fallback defaults if config.py is not found
    EM4_IP = "192.168.1.157"
    EM4_PORT = 502
    EM4_UNIT_ID = 0xFF
    CONNECTION_TIMEOUT = 3.0
    CONNECTION_RETRIES = 1
    DEFAULT_OUTLET = 1
    MIN_CURRENT = 6.0
    MAX_CURRENT = 32.0
    DECIMAL_PLACES_CURRENT = 1
    DECIMAL_PLACES_VOLTAGE = 1
    DECIMAL_PLACES_POWER = 2
    DECIMAL_PLACES_ENERGY = 2

try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.exceptions import ModbusException, ConnectionException
except ImportError:
    print("Error: pymodbus not found. Install with: pip install pymodbus>=3.0")
    sys.exit(1)


# Status code mapping for eM4 EVSE (from official documentation)
STATUS_CODES = {
    0x00A0: "Outlet blocked, EV is recognised",
    0x00A1: "Outlet is waiting for EV", 
    0x00A2: "Outlet reserved",
    0x00B0: "EV recognised, authentication failed",
    0x00B1: "EV recognised, authentication",
    0x00B2: "Outlet can provide energy for charging",
    0x00B3: "EV has ended or interrupted charging",
    0x00C2: "Outlet provides energy for charging (request by EV)",
    0x00E0: "Outlet blocked, EV is not recognised",
    0x00E2: "Outlet in boot process",
    # Error codes (0x00Fx range)
    0x00F0: "Error", 0x00F1: "Error", 0x00F2: "Error", 0x00F3: "Error",
    0x00F4: "Error", 0x00F5: "Error", 0x00F6: "Error", 0x00F7: "Error",
    0x00F8: "Error", 0x00F9: "Error", 0x00FA: "Error", 0x00FB: "Error",
    0x00FC: "Error", 0x00FD: "Error", 0x00FE: "Error", 0x00FF: "Error",
}

# Register address constants
PRODUCT_BASE = 0x0100  # Stand-alone product base
OUTLET_BASE = 0x3000   # Outlet 1 base (outlet n: 0x3000 + 0x0100*(n-1))

# Product offsets
IRATED_OFFSET = 0x23   # Rated current (10*A)
IDEFAULT_OFFSET = 0x24 # Install/limit current (10*A)

# Outlet offsets
CURRENTS_OFFSET = 0x01    # Phase currents L1,L2,L3 (3x uint32, 0.1A)
VOLTAGES_OFFSET = 0x07    # Phase voltages L1,L2,L3 (3x uint32, 0.1V)
POWER_OFFSET = 0x0D       # Active power (uint32, W)
ENERGY_OFFSET = 0x0F      # Energy (uint32, 0.01 kWh)
STATUS_OFFSET = 0x31      # Status (uint16)
ICMAX_OFFSET = 0x32       # EMS max current (uint16, RW, 10*A)
IC_OFFSET = 0x33          # Actual allowed current (uint16, 10*A)


class EM4ModbusClient:
    """Wallbox eM4 EVSE Modbus TCP client"""
    
    def __init__(self):
        self.client: Optional[ModbusTcpClient] = None
        
    def connect(self, ip: str, port: int = 502, unit: int = 0xFF) -> ModbusTcpClient:
        """
        Connect to eM4 EVSE over Modbus TCP
        
        Args:
            ip: IP address of the eM4 device
            port: TCP port (default 502)
            unit: Unit identifier (default 0xFF for eM4)
            
        Returns:
            Connected ModbusTcpClient
            
        Raises:
            ConnectionException: If connection fails after retry
        """
        # Create client with compatible parameters for different pymodbus versions
        try:
            # Try newer pymodbus syntax first
            self.client = ModbusTcpClient(
                host=ip,
                port=port,
                timeout=CONNECTION_TIMEOUT
            )
        except TypeError:
            # Fallback to older pymodbus syntax
            self.client = ModbusTcpClient(ip, port)
        
        if not self.client.connect():
            raise ConnectionException(f"Failed to connect to {ip}:{port}")
            
        return self.client
    
    def read_u16(self, address: int) -> int:
        """Read single 16-bit register"""
        if not self.client:
            raise ConnectionException("Client not connected")
            
        # Try different parameter names for pymodbus compatibility
        try:
            # Modern pymodbus 3.x uses device_id
            result = self.client.read_holding_registers(address, count=1, device_id=0xFF)
        except TypeError:
            try:
                # Older versions use unit
                result = self.client.read_holding_registers(address, 1, unit=0xFF)
            except TypeError:
                # Very old versions use slave
                result = self.client.read_holding_registers(address, 1, slave=0xFF)
            
        if result.isError() or not result.registers:
            raise ModbusException("No response - check IP, unit ID, or firewall")
        return result.registers[0]
    
    def read_u32_pair(self, address: int) -> int:
        """Read two consecutive 16-bit registers as big-endian 32-bit value"""
        if not self.client:
            raise ConnectionException("Client not connected")
            
        # Try different parameter names for pymodbus compatibility
        try:
            # Modern pymodbus 3.x uses device_id
            result = self.client.read_holding_registers(address, count=2, device_id=0xFF)
        except TypeError:
            try:
                # Older versions use unit
                result = self.client.read_holding_registers(address, 2, unit=0xFF)
            except TypeError:
                # Very old versions use slave
                result = self.client.read_holding_registers(address, 2, slave=0xFF)
            
        if result.isError() or len(result.registers) != 2:
            raise ModbusException("No response - check IP, unit ID, or firewall")
        
        # Big-endian: high word first, then low word
        hi, lo = result.registers
        return (hi << 16) | lo
    
    def read_three_u32(self, address: int) -> Tuple[int, int, int]:
        """Read three consecutive 32-bit values (6 registers total)"""
        if not self.client:
            raise ConnectionException("Client not connected")
            
        # Try different parameter names for pymodbus compatibility
        try:
            # Modern pymodbus 3.x uses device_id
            result = self.client.read_holding_registers(address, count=6, device_id=0xFF)
        except TypeError:
            try:
                # Older versions use unit
                result = self.client.read_holding_registers(address, 6, unit=0xFF)
            except TypeError:
                # Very old versions use slave
                result = self.client.read_holding_registers(address, 6, slave=0xFF)
            
        if result.isError() or len(result.registers) != 6:
            raise ModbusException("No response - check IP, unit ID, or firewall")
        
        # Parse as three big-endian 32-bit values
        regs = result.registers
        val1 = (regs[0] << 16) | regs[1]  # L1
        val2 = (regs[2] << 16) | regs[3]  # L2  
        val3 = (regs[4] << 16) | regs[5]  # L3
        return val1, val2, val3
    
    def write_u16(self, address: int, value: int) -> None:
        """Write single 16-bit register using function 16 (write multiple)"""
        if not self.client:
            raise ConnectionException("Client not connected")
            
        # Try different parameter names for pymodbus compatibility
        try:
            # Modern pymodbus 3.x uses device_id
            result = self.client.write_registers(address, [value], device_id=0xFF)
        except TypeError:
            try:
                # Older versions use unit
                result = self.client.write_registers(address, [value], unit=0xFF)
            except TypeError:
                # Very old versions use slave
                result = self.client.write_registers(address, [value], slave=0xFF)
        
        if result.isError():
            raise ModbusException("Write failed - check permissions or device state")
    
    def get_outlet_base(self, outlet: int) -> int:
        """Calculate base address for outlet (1-indexed)"""
        if outlet < 1:
            raise ValueError("Outlet index must be >= 1")
        return OUTLET_BASE + 0x0100 * (outlet - 1)
    
    def read_metrics(self, outlet: int) -> Dict[str, Any]:
        """
        Read all metrics for specified outlet
        
        Args:
            outlet: Outlet number (1-indexed)
            
        Returns:
            Dictionary containing all outlet metrics
        """
        outlet_base = self.get_outlet_base(outlet)
        
        # Read product limits (same for all outlets)
        irated_raw = self.read_u16(PRODUCT_BASE + IRATED_OFFSET)
        idefault_raw = self.read_u16(PRODUCT_BASE + IDEFAULT_OFFSET)
        
        # Read outlet-specific data
        status_raw = self.read_u16(outlet_base + STATUS_OFFSET)
        icmax_raw = self.read_u16(outlet_base + ICMAX_OFFSET) 
        ic_raw = self.read_u16(outlet_base + IC_OFFSET)
        
        # Read phase currents (3x uint32, 0.1A resolution)
        curr_l1, curr_l2, curr_l3 = self.read_three_u32(outlet_base + CURRENTS_OFFSET)
        
        # Read phase voltages (3x uint32, 0.1V resolution)  
        volt_l1, volt_l2, volt_l3 = self.read_three_u32(outlet_base + VOLTAGES_OFFSET)
        
        # Read power and energy
        power_raw = self.read_u32_pair(outlet_base + POWER_OFFSET)  # W
        energy_raw = self.read_u32_pair(outlet_base + ENERGY_OFFSET)  # 0.01 kWh
        
        return {
            'outlet': outlet,
            'status_code': status_raw,
            'status_text': STATUS_CODES.get(status_raw, f"Unknown (0x{status_raw:04X})"),
            'ic_amps': ic_raw / 10.0,
            'icmax_amps': icmax_raw / 10.0, 
            'idefault_amps': idefault_raw / 10.0,
            'irated_amps': irated_raw / 10.0,
            'phase_currents': (curr_l1 / 10.0, curr_l2 / 10.0, curr_l3 / 10.0),
            'phase_voltages': (volt_l1 / 10.0, volt_l2 / 10.0, volt_l3 / 10.0),
            'power_kw': power_raw / 1000.0,
            'energy_kwh': energy_raw / 100.0
        }
    
    def set_icmax(self, outlet: int, amps: float) -> float:
        """
        Set maximum current (Icmax) for specified outlet
        
        Args:
            outlet: Outlet number (1-indexed)
            amps: Desired current in amperes (6-32A)
            
        Returns:
            Confirmed Icmax value in amperes
            
        Raises:
            ValueError: If current exceeds limits
        """
        # Validate input range per eM4 documentation
        # Valid values: 0.0A OR 6.0A-32.0A (no values between 0.1A-5.9A allowed)
        if amps != 0.0 and amps < 6.0:
            raise ValueError(f"Current must be 0.0A or >= 6.0A (got {amps}A)")
        if amps > 32.0:
            raise ValueError(f"Maximum current is 32.0A (got {amps}A)")
        
        # Read current device state for diagnostics
        outlet_base = self.get_outlet_base(outlet)
        
        # Read product limits
        irated_raw = self.read_u16(PRODUCT_BASE + IRATED_OFFSET)
        idefault_raw = self.read_u16(PRODUCT_BASE + IDEFAULT_OFFSET)
        irated_amps = irated_raw / 10.0
        idefault_amps = idefault_raw / 10.0
        
        # Read current device state  
        status_raw = self.read_u16(outlet_base + STATUS_OFFSET)
        current_icmax_raw = self.read_u16(outlet_base + ICMAX_OFFSET)
        current_ic_raw = self.read_u16(outlet_base + IC_OFFSET)
        
        # Check device state and provide user feedback
        status_text = STATUS_CODES.get(status_raw, f"Unknown (0x{status_raw:04X})")
        print(f"Current device status: {status_text}")
        
        if current_icmax_raw > 0:
            print(f"Current Icmax setting: {current_icmax_raw / 10.0}A")
        else:
            print("Current Icmax setting: 0.0A (disabled/waiting)")
            
        # Warn about states where Icmax changes might not work as expected
        if status_raw == 0x00A1:  # Waiting for EV
            print("ℹ️  Note: Device is waiting for EV. Icmax may only apply when EV connects.")
        elif status_raw in [0x00A0, 0x00E0]:  # Blocked states  
            print("⚠️  Warning: Outlet is blocked. Icmax changes may not be accepted.")
        elif status_raw == 0x00E2:  # Boot process
            print("⚠️  Warning: Device is booting. Please wait and try again.")
        elif (status_raw & 0x00F0) == 0x00F0:  # Error states
            print("❌ Warning: Device is in error state. Resolve errors before setting current.")
        
        if amps > idefault_amps:
            raise ValueError(f"Requested {amps}A exceeds installation limit {idefault_amps}A")
        
        # Convert to device units and write
        icmax_raw = int(round(amps * 10))
        
        # Write to Icmax register per official eM4 documentation
        self.write_u16(outlet_base + ICMAX_OFFSET, icmax_raw)
        
        # Read back to confirm (allow device time to process)
        time.sleep(0.5)  # Increased from 0.2s to 0.5s for better reliability
        confirmed_raw = self.read_u16(outlet_base + ICMAX_OFFSET)
        confirmed_amps = confirmed_raw / 10.0
        
        # If first attempt didn't work and we're in active charging, try once more
        if confirmed_amps != amps and status_raw in [0x00B1, 0x00B2, 0x00C1, 0x00C2]:  # Active charging states
            print(f"⚡ First write gave {confirmed_amps}A, retrying...")
            time.sleep(0.2)
            self.write_u16(outlet_base + ICMAX_OFFSET, icmax_raw)
            time.sleep(0.5)
            confirmed_raw = self.read_u16(outlet_base + ICMAX_OFFSET)
            confirmed_amps = confirmed_raw / 10.0
        
        # Explain the result based on device behavior
        if confirmed_amps == amps:
            print(f"✅ Icmax successfully set to {confirmed_amps}A")
        elif confirmed_amps == 0.0 and amps > 0 and status_raw == 0x00A1:
            print(f"ℹ️  Icmax write accepted but shows 0A (normal when waiting for EV)")
            print(f"   Setting will activate when EV connects and charging begins")
        elif confirmed_amps != amps:
            print(f"⚠️  Icmax set to {confirmed_amps}A (different from requested {amps}A)")
            if confirmed_amps == 0.0:
                print("   Device may have rejected the setting due to current state")
        
        return confirmed_amps
    
    def disconnect(self) -> None:
        """Close Modbus connection"""
        if self.client:
            self.client.close()
            self.client = None


def print_metrics(metrics: Dict[str, Any]) -> None:
    """Print metrics in formatted output with bright colors"""
    
    # ANSI bright color codes for better visibility
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Bright colors (90-97 range)
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m' 
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_MAGENTA = '\033[45m'
    
    # Individual phase colors
    L1_COLOR = BRIGHT_RED
    L2_COLOR = BRIGHT_GREEN  
    L3_COLOR = BRIGHT_BLUE
    
    # Status color based on state
    if metrics['status_code'] == 0x00C2:  # Charging
        status_color = f"{BG_GREEN}{BRIGHT_WHITE}{BOLD}"
    elif metrics['status_code'] == 0x00A1:  # Waiting for EV
        status_color = f"{BRIGHT_YELLOW}{BOLD}"
    elif (metrics['status_code'] & 0x00F0) == 0x00F0:  # Error
        status_color = f"{BG_RED}{BRIGHT_WHITE}{BOLD}"
    else:
        status_color = f"{BRIGHT_CYAN}{BOLD}"
    
    print(f"Outlet {BRIGHT_CYAN}{BOLD}{metrics['outlet']}{RESET}  | Status: {status_color}{metrics['status_text']}{RESET} (0x{metrics['status_code']:04X})")
    
    # Current values with distinct colors
    ic_color = f"{BG_GREEN}{BRIGHT_WHITE}{BOLD}" if metrics['ic_amps'] > 0 else BRIGHT_WHITE
    icmax_color = f"{BRIGHT_BLUE}{BOLD}" if metrics['icmax_amps'] > 0 else BRIGHT_WHITE
    idefault_color = f"{BRIGHT_YELLOW}"
    irated_color = f"{BRIGHT_MAGENTA}"
    
    print(f"{BRIGHT_CYAN}Ic{RESET} / {BRIGHT_CYAN}Icmax{RESET} / {BRIGHT_CYAN}Idefault{RESET} / {BRIGHT_CYAN}Irated{RESET}: {ic_color}{metrics['ic_amps']:.{DECIMAL_PLACES_CURRENT}f} A{RESET} / {icmax_color}{metrics['icmax_amps']:.{DECIMAL_PLACES_CURRENT}f} A{RESET} / {idefault_color}{metrics['idefault_amps']:.{DECIMAL_PLACES_CURRENT}f} A{RESET} / {irated_color}{metrics['irated_amps']:.{DECIMAL_PLACES_CURRENT}f} A{RESET}")
    
    # Phase currents with individual L1/L2/L3 colors
    curr = metrics['phase_currents']
    l1_current_color = f"{BG_RED}{BRIGHT_WHITE}{BOLD}" if curr[0] > 0.1 else L1_COLOR
    l2_current_color = f"{BG_GREEN}{BRIGHT_WHITE}{BOLD}" if curr[1] > 0.1 else L2_COLOR
    l3_current_color = f"{BG_BLUE}{BRIGHT_WHITE}{BOLD}" if curr[2] > 0.1 else L3_COLOR
    
    print(f"{BRIGHT_CYAN}Phase I [A]{RESET}: {L1_COLOR}L1{RESET}={l1_current_color}{curr[0]:.{DECIMAL_PLACES_CURRENT}f}{RESET}  {L2_COLOR}L2{RESET}={l2_current_color}{curr[1]:.{DECIMAL_PLACES_CURRENT}f}{RESET}  {L3_COLOR}L3{RESET}={l3_current_color}{curr[2]:.{DECIMAL_PLACES_CURRENT}f}{RESET}")
    
    # Phase voltages with individual L1/L2/L3 colors
    volt = metrics['phase_voltages']
    v1_voltage_color = f"{BRIGHT_CYAN}{BOLD}" if 200 < volt[0] < 250 else f"{BRIGHT_YELLOW}{BOLD}" if volt[0] > 0 else BRIGHT_WHITE
    v2_voltage_color = f"{BRIGHT_CYAN}{BOLD}" if 200 < volt[1] < 250 else f"{BRIGHT_YELLOW}{BOLD}" if volt[1] > 0 else BRIGHT_WHITE
    v3_voltage_color = f"{BRIGHT_CYAN}{BOLD}" if 200 < volt[2] < 250 else f"{BRIGHT_YELLOW}{BOLD}" if volt[2] > 0 else BRIGHT_WHITE
    
    print(f"{BRIGHT_CYAN}Phase U [V]{RESET}: {L1_COLOR}L1{RESET}={v1_voltage_color}{volt[0]:.{DECIMAL_PLACES_VOLTAGE}f}{RESET} {L2_COLOR}L2{RESET}={v2_voltage_color}{volt[1]:.{DECIMAL_PLACES_VOLTAGE}f}{RESET} {L3_COLOR}L3{RESET}={v3_voltage_color}{volt[2]:.{DECIMAL_PLACES_VOLTAGE}f}{RESET}")
    
    # Power with background when active
    power_color = f"{BG_MAGENTA}{BRIGHT_WHITE}{BOLD}" if metrics['power_kw'] > 0 else BRIGHT_WHITE
    print(f"{BRIGHT_CYAN}Active Power{RESET}: {power_color}{metrics['power_kw']:.{DECIMAL_PLACES_POWER}f} kW{RESET}")
    
    # Energy with bright blue
    print(f"{BRIGHT_CYAN}Energy{RESET}: {BRIGHT_BLUE}{BOLD}{metrics['energy_kwh']:.{DECIMAL_PLACES_ENERGY}f} kWh{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Wallbox eM4 EVSE Modbus TCP Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s read                    # Read using config.py settings
  %(prog)s --outlet 2 read         # Read outlet 2
  %(prog)s --ip 192.168.1.50 read  # Override IP address
  %(prog)s set-icmax 16            # Set max current to 16A

Requirements:
  pip install pymodbus>=3.0
        """
    )
    
    parser.add_argument('--ip', default=EM4_IP, help=f'eM4 IP address (default: {EM4_IP})')
    parser.add_argument('--outlet', type=int, default=DEFAULT_OUTLET, help=f'Outlet number (default: {DEFAULT_OUTLET})')
    parser.add_argument('--port', type=int, default=EM4_PORT, help=f'Modbus TCP port (default: {EM4_PORT})')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Read command
    subparsers.add_parser('read', help='Read outlet metrics')
    
    # Set-icmax command
    set_parser = subparsers.add_parser('set-icmax', help='Set maximum current')
    set_parser.add_argument('amps', type=float, help=f'Current in amperes ({MIN_CURRENT}-{MAX_CURRENT}A)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    client = EM4ModbusClient()
    
    try:
        # Connect to device
        client.connect(args.ip, args.port)
        print(f"Connected to eM4 at {args.ip}:{args.port}")
        
        if args.command == 'read':
            metrics = client.read_metrics(args.outlet)
            print()
            print_metrics(metrics)
            
        elif args.command == 'set-icmax':
            print(f"Setting Icmax to {args.amps} A for outlet {args.outlet}...")
            confirmed = client.set_icmax(args.outlet, args.amps)
            print(f"Icmax confirmed: {confirmed:.{DECIMAL_PLACES_CURRENT}f} A")
            
    except (ConnectionException, ModbusException) as e:
        print(f"Error: {e}")
        return 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    finally:
        client.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())