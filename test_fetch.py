import os
from fusion_solar_py.client import FusionSolarClient

FS_USER = os.environ.get("FUSIONSOLAR_USER", "deputynl")
FS_PASSWORD = os.environ["FUSIONSOLAR_PASSWORD"]
FS_SUBDOMAIN = os.environ.get("FUSIONSOLAR_SUBDOMAIN", "uni005eu5")

print(f"Connecting to {FS_SUBDOMAIN}.fusionsolar.huawei.com as {FS_USER} ...")
client = FusionSolarClient(FS_USER, FS_PASSWORD, huawei_subdomain=FS_SUBDOMAIN)

print("\n--- Power Status ---")
status = client.get_power_status()
print(f"  current_power_kw  : {status.current_power_kw}")
print(f"  energy_today_kwh  : {status.energy_today_kwh}")
print(f"  energy_total_kwh  : {status.energy_kwh}")

print("\n--- Station List ---")
stations = client.get_station_list()
for s in stations:
    print(f"  {s}")
