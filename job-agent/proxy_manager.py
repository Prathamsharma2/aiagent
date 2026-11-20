import time
import requests
from stem import Signal
from stem.control import Controller

class ProxyManager:
    def __init__(self, tor_proxy="socks5h://127.0.0.1:9050", control_port=9051):
        self.proxies = {
            "http": tor_proxy,
            "https": tor_proxy
        }
        self.control_port = control_port

    def get_ip(self):
        """Check current exit node IP."""
        try:
            r = requests.get("https://httpbin.org/ip", proxies=self.proxies, timeout=10)
            return r.json().get("origin")
        except Exception as e:
            return f"Error: {e}"

    def rotate_ip(self):
        """Signal Tor to change the circuit (get a new IP)."""
        print("🔄 Rotating Tor IP...")
        try:
            with Controller.from_port(port=self.control_port) as controller:
                controller.authenticate()  # Requires password if set in torrc
                controller.signal(Signal.NEWNYM)
            time.sleep(5)  # Wait for circuit setup
            return True
        except Exception as e:
            print(f"❌ Failed to rotate IP: {e}")
            return False

# Example usage:
if __name__ == "__main__":
    pm = ProxyManager()
    print(f"Current IP: {pm.get_ip()}")
    pm.rotate_ip()
    print(f"New IP: {pm.get_ip()}")
