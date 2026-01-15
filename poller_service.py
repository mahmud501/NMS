import time
from modules.availability import poll_device_availability
from modules.device_health import poll_device_health
from modules.interface_poller import poll_interfaces
from modules.arp_poller import poll_arp
from modules.cdp_poller import poll_cdp

# def start_polling_service(interval_minutes=5):
#     """
#     Start a continuous polling service that runs every interval_minutes.
#     """
#     print(f"Starting availability polling service (interval: {interval_minutes} minutes)...")
#     while True:
#         try:
#             poll_device_availability()
#             poll_device_health()
#             poll_interfaces()
#             poll_arp()
#             poll_cdp()
#         except Exception as e:
#             print(f"Error during polling: {e}")
#         time.sleep(interval_minutes * 60)

def start_polling_service():
    """
    Polling device data in custom intervals.
    """
    print("Starting polling service...")
    last_availability_poll = 0
    last_health_poll = 0
    last_interface_poll = 0
    last_arp_poll = 0
    last_cdp_poll = 0

    while True:
        current_time = time.time()
        if current_time - last_availability_poll >= 300:  # 5 minutes
            try:
                poll_device_availability()
            except Exception as e:
                print(f"Error during availability polling: {e}")
            last_availability_poll = current_time
        if current_time - last_health_poll >= 300:
            try:
                poll_device_health()
            except Exception as e:
                print(f"Error during health polling: {e}")
            last_health_poll = current_time

        if current_time - last_arp_poll >= 600: 
            try:
                poll_arp()
            except Exception as e:
                print(f"Error during ARP polling: {e}")
            last_arp_poll = current_time
        if current_time - last_cdp_poll >= 1800:
            try:
                poll_cdp()
            except Exception as e:
                print(f"Error during CDP polling: {e}")
            last_cdp_poll = current_time

        if current_time - last_interface_poll >= 300:
            try:
                poll_interfaces()
            except Exception as e:
                print(f"Error during interface polling: {e}")
            last_interface_poll = current_time
            
        time.sleep(60) # Sleep for 1 minute between checks

if __name__ == "__main__":
    # Run once for testing
    #poll_device_availability()
    
    # Uncomment to start continuous service
    # start_polling_service(interval_minutes=5)
    start_polling_service()
    
