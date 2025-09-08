#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wallbox eM4 EVSE Interactive Interface

Simple menu-driven interface for controlling and monitoring eM4 charging stations.
"""

import os
import sys
import time

# Fix Windows console encoding
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
from typing import Optional

try:
    from em4_modbus import EM4ModbusClient, print_metrics
    from config import EM4_IP, EM4_PORT, DEFAULT_OUTLET, MIN_CURRENT, MAX_CURRENT
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure em4_modbus.py and config.py are in the same directory.")
    sys.exit(1)


class EM4Interface:
    """Interactive interface for eM4 EVSE control"""
    
    def __init__(self):
        self.client = EM4ModbusClient()
        self.connected = False
        self.current_ip = EM4_IP
        self.current_port = EM4_PORT
        self.current_outlet = DEFAULT_OUTLET
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print the interface header"""
        print("=" * 60)
        print("           Wallbox eM4 EVSE Control Interface")
        print("=" * 60)
        if self.connected:
            print(f"📡 Connected to: {self.current_ip}:{self.current_port}")
        else:
            print(f"❌ Not connected to: {self.current_ip}:{self.current_port}")
        print(f"⚡ Current outlet: {self.current_outlet}")
        print("-" * 60)
    
    def print_menu(self):
        """Print the main menu options"""
        print("\nAvailable Commands:")
        print("1. 📊 Live Metrics Monitor (200ms refresh)")
        print("2. ⚡ Set Maximum Current (Icmax)")
        print("3. 🔌 Change Outlet Number")
        print("4. 🌐 Change IP Address")
        print("5. 🔄 Reconnect to Device")
        print("6. ❓ Show Help")
        print("0. 🚪 Exit")
        print("-" * 60)
    
    def connect_to_device(self) -> bool:
        """Connect to the eM4 device"""
        try:
            print(f"🔗 Connecting to eM4 at {self.current_ip}:{self.current_port}...")
            self.client.connect(self.current_ip, self.current_port)
            self.connected = True
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.connected = False
            return False
    
    def read_metrics(self):
        """Read and display eM4 metrics with continuous refresh"""
        if not self.connected:
            print("❌ Not connected to device. Use option 5 to reconnect.")
            return
            
        print(f"📊 Live metrics for outlet {self.current_outlet}")
        print("Press 'q' to stop, or Ctrl+C to exit")
        print("⚡ Quick Controls: [0]=Pause  [1]=6A  [2]=10A  [3]=20A  [4]=32A")
        print("=" * 70)
        
        try:
            # Print static headers once
            print("Status          :")
            print("Ic / Icmax / Idefault / Irated :")
            print("Phase I [A]     : L1=         L2=         L3=")
            print("Phase U [V]     : L1=         L2=         L3=")
            print("Active Power    :")
            print("Energy          :")
            print()
            print("🔄 Refreshing every 200ms... (Press 'q' to stop)")
            
            while True:
                try:
                    metrics = self.client.read_metrics(self.current_outlet)
                    
                    # Move cursor up to overwrite values (7 lines up)
                    print('\033[7A', end='')
                    
                    # Update each line with new values
                    self.print_metrics_inline(metrics)
                    
                    # Sleep for refresh interval
                    time.sleep(0.2)
                    
                    # Check for user input (Windows compatible)
                    import msvcrt
                    if os.name == 'nt':  # Windows
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            if key.lower() == b'q':
                                print("\nStopping refresh...")
                                break
                            elif key == b'0':
                                self.quick_set_icmax(0.0, "Pause")
                            elif key == b'1':
                                self.quick_set_icmax(6.0, "6A")
                            elif key == b'2':
                                self.quick_set_icmax(10.0, "10A")
                            elif key == b'3':
                                self.quick_set_icmax(20.0, "20A")
                            elif key == b'4':
                                self.quick_set_icmax(32.0, "32A")
                    else:  # Unix/Linux/Mac
                        import select
                        import sys
                        ready, _, _ = select.select([sys.stdin], [], [], 0)
                        if ready:
                            user_input = sys.stdin.readline().strip().lower()
                            if user_input == 'q':
                                break
                            elif user_input == '0':
                                self.quick_set_icmax(0.0, "Pause")
                            elif user_input == '1':
                                self.quick_set_icmax(6.0, "6A")
                            elif user_input == '2':
                                self.quick_set_icmax(10.0, "10A")
                            elif user_input == '3':
                                self.quick_set_icmax(20.0, "20A")
                            elif user_input == '4':
                                self.quick_set_icmax(32.0, "32A")
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Error reading metrics: {e}")
                    self.connected = False
                    break
                    
        except KeyboardInterrupt:
            pass
        finally:
            print("\n📊 Metrics monitoring stopped.")
    
    def quick_set_icmax(self, amps, label):
        """Quick Icmax setting during live monitoring"""
        try:
            print(f"\n⚡ {label}...")
            confirmed = self.client.set_icmax(self.current_outlet, amps)
            if confirmed == amps:
                print(f"✅ {label} confirmed")
            else:
                print(f"⚠️  Set to {confirmed}A (requested {amps}A)")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Brief pause to show result before continuing refresh
        time.sleep(0.5)
    
    def print_metrics_inline(self, metrics):
        """Print metrics values in-place without refreshing static text"""
        from config import DECIMAL_PLACES_CURRENT, DECIMAL_PLACES_VOLTAGE, DECIMAL_PLACES_POWER, DECIMAL_PLACES_ENERGY
        
        # ANSI bright/light color codes for better visibility
        RESET = '\033[0m'
        BOLD = '\033[1m'
        
        # Bright/Light colors (90-97 range)
        BRIGHT_RED = '\033[91m'
        BRIGHT_GREEN = '\033[92m' 
        BRIGHT_YELLOW = '\033[93m'
        BRIGHT_BLUE = '\033[94m'
        BRIGHT_MAGENTA = '\033[95m'
        BRIGHT_CYAN = '\033[96m'
        BRIGHT_WHITE = '\033[97m'
        
        # Background colors for emphasis
        BG_RED = '\033[41m'
        BG_GREEN = '\033[42m'
        BG_YELLOW = '\033[43m'
        BG_BLUE = '\033[44m'
        BG_MAGENTA = '\033[45m'
        BG_CYAN = '\033[46m'
        
        # Individual phase colors for L1, L2, L3
        L1_COLOR = BRIGHT_RED     # L1 = Bright Red
        L2_COLOR = BRIGHT_GREEN   # L2 = Bright Green  
        L3_COLOR = BRIGHT_BLUE    # L3 = Bright Blue
        
        # Status color based on state (with background for important states)
        if metrics['status_code'] == 0x00C2:  # Charging - bright green background
            status_color = f"{BG_GREEN}{BRIGHT_WHITE}{BOLD}"
        elif metrics['status_code'] == 0x00A1:  # Waiting for EV - bright yellow
            status_color = f"{BRIGHT_YELLOW}{BOLD}"
        elif (metrics['status_code'] & 0x00F0) == 0x00F0:  # Error - red background
            status_color = f"{BG_RED}{BRIGHT_WHITE}{BOLD}"
        elif metrics['status_code'] == 0x00B2:  # Ready to charge - cyan
            status_color = f"{BRIGHT_CYAN}{BOLD}"
        else:
            status_color = f"{BRIGHT_WHITE}"
        
        # Update each line by overwriting with exact positioning
        # Status line with enhanced formatting
        print(f"\r{BRIGHT_CYAN}Status{RESET}          : {status_color}{metrics['status_text']:<50}{RESET}", end='')
        print('\033[K')  # Clear to end of line
        
        # Current values line with distinct colors for each value
        ic_color = f"{BG_GREEN}{BRIGHT_WHITE}{BOLD}" if metrics['ic_amps'] > 0 else f"{BRIGHT_WHITE}"
        icmax_color = f"{BRIGHT_BLUE}{BOLD}" if metrics['icmax_amps'] > 0 else f"{BRIGHT_WHITE}"
        idefault_color = f"{BRIGHT_YELLOW}"
        irated_color = f"{BRIGHT_MAGENTA}"
        
        print(f"\r{BRIGHT_CYAN}Ic{RESET} / {BRIGHT_CYAN}Icmax{RESET} / {BRIGHT_CYAN}Idefault{RESET} / {BRIGHT_CYAN}Irated{RESET} : {ic_color}{metrics['ic_amps']:.{DECIMAL_PLACES_CURRENT}f}A{RESET} / {icmax_color}{metrics['icmax_amps']:.{DECIMAL_PLACES_CURRENT}f}A{RESET} / {idefault_color}{metrics['idefault_amps']:.{DECIMAL_PLACES_CURRENT}f}A{RESET} / {irated_color}{metrics['irated_amps']:.{DECIMAL_PLACES_CURRENT}f}A{RESET}", end='')
        print('\033[K')  # Clear to end of line
        
        # Phase currents line with individual L1/L2/L3 colors
        curr = metrics['phase_currents']
        l1_current_color = f"{BG_RED}{BRIGHT_WHITE}{BOLD}" if curr[0] > 0.1 else L1_COLOR
        l2_current_color = f"{BG_GREEN}{BRIGHT_WHITE}{BOLD}" if curr[1] > 0.1 else L2_COLOR  
        l3_current_color = f"{BG_BLUE}{BRIGHT_WHITE}{BOLD}" if curr[2] > 0.1 else L3_COLOR
        
        print(f"\r{BRIGHT_CYAN}Phase I [A]{RESET}     : {L1_COLOR}L1{RESET}={l1_current_color}{curr[0]:6.{DECIMAL_PLACES_CURRENT}f}{RESET} {L2_COLOR}L2{RESET}={l2_current_color}{curr[1]:6.{DECIMAL_PLACES_CURRENT}f}{RESET} {L3_COLOR}L3{RESET}={l3_current_color}{curr[2]:6.{DECIMAL_PLACES_CURRENT}f}{RESET}", end='')
        print('\033[K')  # Clear to end of line
        
        # Phase voltages line with individual L1/L2/L3 colors and voltage status
        volt = metrics['phase_voltages']
        v1_voltage_color = f"{BRIGHT_CYAN}{BOLD}" if 200 < volt[0] < 250 else f"{BRIGHT_YELLOW}{BOLD}" if volt[0] > 0 else f"{BRIGHT_WHITE}"
        v2_voltage_color = f"{BRIGHT_CYAN}{BOLD}" if 200 < volt[1] < 250 else f"{BRIGHT_YELLOW}{BOLD}" if volt[1] > 0 else f"{BRIGHT_WHITE}"
        v3_voltage_color = f"{BRIGHT_CYAN}{BOLD}" if 200 < volt[2] < 250 else f"{BRIGHT_YELLOW}{BOLD}" if volt[2] > 0 else f"{BRIGHT_WHITE}"
        
        print(f"\r{BRIGHT_CYAN}Phase U [V]{RESET}     : {L1_COLOR}L1{RESET}={v1_voltage_color}{volt[0]:6.{DECIMAL_PLACES_VOLTAGE}f}{RESET} {L2_COLOR}L2{RESET}={v2_voltage_color}{volt[1]:6.{DECIMAL_PLACES_VOLTAGE}f}{RESET} {L3_COLOR}L3{RESET}={v3_voltage_color}{volt[2]:6.{DECIMAL_PLACES_VOLTAGE}f}{RESET}", end='')
        print('\033[K')  # Clear to end of line
        
        # Power line with background when active
        power_color = f"{BG_MAGENTA}{BRIGHT_WHITE}{BOLD}" if metrics['power_kw'] > 0 else f"{BRIGHT_WHITE}"
        print(f"\r{BRIGHT_CYAN}Active Power{RESET}    : {power_color}{metrics['power_kw']:8.{DECIMAL_PLACES_POWER}f} kW{RESET}", end='')
        print('\033[K')  # Clear to end of line
        
        # Energy line with bright blue
        print(f"\r{BRIGHT_CYAN}Energy{RESET}          : {BRIGHT_BLUE}{BOLD}{metrics['energy_kwh']:10.{DECIMAL_PLACES_ENERGY}f} kWh{RESET}", end='')
        print('\033[K')  # Clear to end of line
        
        print()  # Move to refresh line
    
    def set_icmax(self):
        """Set the maximum current (Icmax)"""
        if not self.connected:
            print("❌ Not connected to device. Use option 5 to reconnect.")
            return
            
        try:
            print(f"⚡ Setting maximum current for outlet {self.current_outlet}")
            print(f"Valid range: {MIN_CURRENT} - {MAX_CURRENT} A")
            
            while True:
                try:
                    amps_str = input(f"Enter new Icmax value (A) [or 'cancel']: ").strip()
                    if amps_str.lower() == 'cancel':
                        print("Operation cancelled.")
                        return
                    
                    amps = float(amps_str)
                    break
                except ValueError:
                    print("❌ Invalid input. Please enter a number.")
            
            print(f"🔄 Setting Icmax to {amps} A...")
            confirmed = self.client.set_icmax(self.current_outlet, amps)
            print(f"✅ Icmax confirmed: {confirmed} A")
            
        except ValueError as e:
            print(f"❌ Validation error: {e}")
        except Exception as e:
            print(f"❌ Error setting Icmax: {e}")
            self.connected = False
    
    def change_outlet(self):
        """Change the current outlet number"""
        print(f"🔌 Current outlet: {self.current_outlet}")
        
        while True:
            try:
                outlet_str = input("Enter outlet number (1-8) [or 'cancel']: ").strip()
                if outlet_str.lower() == 'cancel':
                    print("Operation cancelled.")
                    return
                
                outlet = int(outlet_str)
                if outlet < 1:
                    print("❌ Outlet number must be >= 1")
                    continue
                    
                self.current_outlet = outlet
                print(f"✅ Outlet changed to {outlet}")
                break
                
            except ValueError:
                print("❌ Invalid input. Please enter a number.")
    
    def change_ip(self):
        """Change the IP address"""
        print(f"🌐 Current IP: {self.current_ip}")
        
        new_ip = input("Enter new IP address [or 'cancel']: ").strip()
        if new_ip.lower() == 'cancel':
            print("Operation cancelled.")
            return
            
        if new_ip:
            self.current_ip = new_ip
            self.connected = False  # Force reconnection
            print(f"✅ IP changed to {new_ip}")
            print("⚠️  You'll need to reconnect (option 5)")
    
    def show_help(self):
        """Show help information"""
        print("\n📖 Help Information")
        print("-" * 40)
        print("Status Codes:")
        print("  • Ready to charge: Device ready, waiting for EV")
        print("  • Charging: Actively charging an EV")  
        print("  • Waiting for EV: EV not connected")
        print("  • Error codes: Check device and wiring")
        print()
        print("Current Values:")
        print("  • Ic: Current being delivered to EV")
        print("  • Icmax: Your maximum limit setting")
        print("  • Idefault: Installation/safety limit")
        print("  • Irated: Device maximum capacity")
        print()
        print("Power Display:")
        print("  • Phase I/U: Per-phase current/voltage")
        print("  • Active Power: Current power draw (kW)")
        print("  • Energy: Total energy consumed (kWh)")
        print()
        print("Tips:")
        print("  • Icmax cannot exceed Idefault")
        print("  • Setting Icmax = 0 will stop charging")
        print("  • Changes take effect immediately")
    
    def wait_for_enter(self):
        """Wait for user to press Enter"""
        input("\nPress Enter to continue...")
    
    def run(self):
        """Main interface loop"""
        print("🚀 Starting eM4 Interface...")
        
        # Initial connection attempt
        self.connect_to_device()
        
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu()
            
            try:
                choice = input("Select option (0-6): ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                elif choice == '1':
                    self.read_metrics()
                    self.wait_for_enter()
                elif choice == '2':
                    self.set_icmax()
                    self.wait_for_enter()
                elif choice == '3':
                    self.change_outlet()
                    self.wait_for_enter()
                elif choice == '4':
                    self.change_ip()
                    self.wait_for_enter()
                elif choice == '5':
                    self.connect_to_device()
                    self.wait_for_enter()
                elif choice == '6':
                    self.show_help()
                    self.wait_for_enter()
                else:
                    print("❌ Invalid option. Please select 0-6.")
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                self.wait_for_enter()
        
        # Cleanup
        if self.connected:
            self.client.disconnect()


def main():
    """Entry point"""
    interface = EM4Interface()
    
    try:
        interface.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1
    finally:
        if interface.connected:
            interface.client.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())