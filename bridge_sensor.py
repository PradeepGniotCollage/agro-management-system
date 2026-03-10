import serial
import socket
import time
import sys

# --- CONFIGURATION ---
# IMPORTANT: Open Device Manager on Windows to see your Arduino's COM port (e.g., COM3, COM4, COM5)
SERIAL_PORT = 'COM4'   # <--- Change this to your real Arduino port!
BAUD_RATE = 115200
BRIDGE_HOST = '0.0.0.0'
BRIDGE_PORT = 7777
# ---------------------

def run_bridge():
    print("="*50)
    print(" REAL-TIME SOIL SENSOR HARDWARE BRIDGE ")
    print("="*50)
    print(f" Reading from: {SERIAL_PORT} @ {BAUD_RATE}")
    print(f" Listening on: {BRIDGE_HOST}:{BRIDGE_PORT}")
    print("-"*50)
    
    last_cached_data = None
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1) 
        print(f" [SUCCESS] Connected to {SERIAL_PORT} successfully.")
    except Exception as e:
        print("\n" + "!"*50)
        print(f" [HARDWARE ERROR] Could not open {SERIAL_PORT}")
        print(f" REASON: {e}")
        print("\n QUICK CHECKLIST:")
        print(" 1. Is the Arduino plugged in?")
        print(f" 2. Is Device Manager showing your Arduino on {SERIAL_PORT}?")
        print(" 3. IMPORTANT: Is the Arduino Serial Monitor CLOSED? (Only 1 program can use COM4 at once)")
        print("!"*50 + "\n")
        sys.exit(1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((BRIDGE_HOST, BRIDGE_PORT))
        s.listen(1)
        
        while True:
            print(f"\n [BRIDGE READY] Waiting for data from Sensor or connection from App...")
            
            # Start a listener loop that also prints raw data to the console
            conn = None
            try:
                # We use a non-blocking or timeout approach to show raw data even if no app is connected
                s.settimeout(0.5)
                try:
                    conn, addr = s.accept()
                    print(f" [APP CONNECTED] Source: {addr}")
                    # If we have cached data, send it immediately for instant status
                    if last_cached_data:
                        print(f" [INSTANT SEND] Sending cached data to {addr}")
                        conn.sendall(last_cached_data + b"\n")
                except socket.timeout:
                    # Periodically check for serial data even when app is not connected
                    if ser.in_waiting > 0:
                        raw_data = ser.read(ser.in_waiting)
                        if raw_data:
                            last_cached_data = raw_data.strip()
                            print(f" [CACHE UPDATED] {last_cached_data.decode('utf-8', errors='ignore')}")
                    continue

                if conn:
                    last_heartbeat = time.time()
                    while True:
                        if ser.in_waiting > 0:
                            data = ser.read(ser.in_waiting)
                            raw_line = data.decode('utf-8', errors='ignore').strip()
                            if raw_line:
                                print(f" [FORWARDING] {len(data)} bytes: {raw_line}")
                                last_cached_data = data.strip()
                            conn.sendall(data)
                            last_heartbeat = time.time()
                        
                        # Heartbeat every 10 seconds if idle
                        if time.time() - last_heartbeat > 10:
                            print(" [IDLE] Bridge active, waiting for Sensor data...")
                            last_heartbeat = time.time()

                        time.sleep(0.01)
            except (ConnectionResetError, BrokenPipeError):
                print(" [APP DISCONNECTED] Connection closed by the app.")
            except Exception as e:
                print(f" [BRIDGE ERROR] {e}")
            finally:
                if conn:
                    conn.close()

if __name__ == "__main__":
    run_bridge()
