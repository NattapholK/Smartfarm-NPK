import minimalmodbus
import serial.tools.list_ports
import time

# --- Serial Port Settings ---
DEFAULT_SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 4800
BYTESIZE = 8
PARITY = minimalmodbus.serial.PARITY_NONE
STOPBITS = 1
TIMEOUT = 1
SLAVE_ADDRESS = 1 # Modbus Device ID: 1

# --- Function to find and select Serial Port ---
def find_and_select_serial_port():
    """
    Finds available serial ports and attempts to select a suitable one.
    """
    print("\n--- Searching for available Serial Ports ---") # เปิด Log
    available_ports = serial.tools.list_ports.comports()

    if not available_ports:
        print("❌ No Serial Ports found in the system.") # เปิด Log
        print("  - Please check if your USB-to-Serial converter or Modbus device is connected.") # เปิด Log
        return None

    print("\n--- Detected Serial Ports ---") # เปิด Log
    selected_port = None
    for port_info in sorted(available_ports):
        print(f"  - Name: {port_info.device}, Description: {port_info.description}, Hardware ID: {port_info.hwid}") # เปิด Log
        if 'USB' in port_info.description.upper() or 'USB' in port_info.hwid.upper():
            if 'BLUETOOTH' not in port_info.description.upper() and not selected_port: 
                selected_port = port_info.device
                print(f"  ✅ Selected this USB port as primary: {selected_port}") # เปิด Log
            elif selected_port and 'BLUETOOTH' not in port_info.description.upper():
                print(f"  (Other USB ports found: {port_info.device})") # เปิด Log

    if selected_port:
        print(f"\n✅ Automatically selected port: {selected_port}") # เปิด Log
        return selected_port
    else:
        print(f"\n❗ Could not automatically identify a suitable Serial Port.") # เปิด Log
        print(f"  - Please check your Serial Port and set 'DEFAULT_SERIAL_PORT' in the code manually (currently: '{DEFAULT_SERIAL_PORT}')") # เปิด Log
        return None

# --- Function to get sensor data ---
def get_sensor_data():
    """
    Reads data from the Modbus sensor and returns it as a dictionary.
    """
    current_serial_port = find_and_select_serial_port() or DEFAULT_SERIAL_PORT

    sensor = None
    try:
        sensor = minimalmodbus.Instrument(current_serial_port, SLAVE_ADDRESS)
        sensor.serial.baudrate = BAUDRATE
        sensor.serial.bytesize = BYTESIZE
        sensor.serial.parity = PARITY
        sensor.serial.stopbits = STOPBITS
        sensor.serial.timeout = TIMEOUT
        print(f"\n--- Modbus Sensor setup complete on port {current_serial_port} ---") # เปิด Log
    except Exception as e:
        print(f"❌ Error setting up Modbus Sensor: {e}")
        print("  - Check serial connection, port access permissions.")
        print("  - Run `sudo usermod -a -G dialout $USER` and reboot Raspberry Pi")
        return {"error": f"Sensor setup failed: {e}"}

    try:
        # Read values from Modbus sensor
        humidity_raw = sensor.read_register(0, 0, functioncode=3, signed=False)
        humidity = humidity_raw / 10.0

        temperature_raw = sensor.read_register(1, 0, functioncode=3, signed=True)
        temperature = temperature_raw / 10.0
        
        ec_raw = sensor.read_register(2, 0, functioncode=3, signed=False)
        ec = ec_raw 
        
        ph_raw = sensor.read_register(3, 0, functioncode=3, signed=False)
        ph = ph_raw / 10.0
        
        nitrogen_raw = sensor.read_register(4, 0, functioncode=3, signed=False)
        nitrogen = nitrogen_raw

        phosphorus_raw = sensor.read_register(5, 0, functioncode=3, signed=False)
        phosphorus = phosphorus_raw

        potassium_raw = sensor.read_register(6, 0, functioncode=3, signed=False)
        potassium = potassium_raw

        sensor_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "humidity": round(humidity, 1),
            "temperature": round(temperature, 1),
            "ec": ec,
            "ph": round(ph, 1),
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium
        }
        print(f"✅ Sensor data read: {sensor_data}") # เปิด Log
        return sensor_data

    except minimalmodbus.ModbusException as e:
        print(f"❌ Modbus Error: {e}")
        return {"error": f"Modbus communication error: {e}"}
    except serial.SerialException as e:
        print(f"❌ Serial Port Error: {e}")
        return {"error": f"Serial port issue: {e}"}
    except Exception as e:
        print(f"❌ Unexpected Error during reading: {e}")
        return {"error": f"Unexpected error: {e}"}
    finally:
        if sensor and sensor.serial.is_open:
            sensor.serial.close()
            print("Modbus serial connection closed.") # เปิด Log

if __name__ == '__main__':
    # This block is for testing get_sensor_data directly
    data = get_sensor_data()
    if "error" not in data:
        print("Test read successful:", data)
    else:
        print("Test read failed:", data["error"])
