from modules.oids import get_device_model

# query = " SELECT device_id, ip_address, hostname, status, model, serial_number, os_version, uptime FROM devices"
# query += " WHERE status = 'up'"
# print(query)
# from modules.utils import format_time
# print(format_time(12700788))

# # Test it
# print(format_time(12700788))  # → 1d 11h 16m 47s
# print(format_time(45))        # → 45s
# print(format_time(3661))      # → 1h 1m 1s
# print(format_time(90061))     # → 1d 1h 1m 1s
# print(format_time(0))         # → 0s
model = get_device_model("enterprises.9.1.222")
print(model)