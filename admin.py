import os
import hmac
import hashlib
import win32com.client
import logging

SECRET_KEY = b"4654365f-a510-47b4-a2b6-e2bf1993f0ef"

SAVE_FOLDER = os.path.join(os.path.expanduser("~"), ".usbsentile")

logging.basicConfig(
    filename=os.path.join(SAVE_FOLDER, "usb_sentinel.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_event(message: str, level="info"):
    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)


def list_usb_drives_with_details():
    try:
        wmi = win32com.client.GetObject("winmgmts:")
        usb_drives = []

        physical_disks = wmi.ExecQuery(
            "SELECT * FROM Win32_DiskDrive WHERE InterfaceType = 'USB'"
        )

        disk_info = {}
        for disk in physical_disks:
            disk_number = disk.Index
            serial_number = getattr(disk, 'SerialNumber', '').strip()
            disk_info[disk_number] = {
                'SerialNumber': serial_number if serial_number else "Unknown",
                'Model': disk.Model
            }

        logical_disks = wmi.ExecQuery(
            "SELECT * FROM Win32_LogicalDisk WHERE DriveType = 2"
        )

        for logical_disk in logical_disks:
            partitions = wmi.ExecQuery(
                f"ASSOCIATORS OF {{Win32_LogicalDisk.DeviceID='{logical_disk.DeviceID}'}} "
                "WHERE AssocClass = Win32_LogicalDiskToPartition"
            )
            
            for partition in partitions:
                disk_drives = wmi.ExecQuery(
                    f"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partition.DeviceID}'}} "
                    "WHERE AssocClass = Win32_DiskDriveToDiskPartition"
                )
                
                for disk_drive in disk_drives:
                    if disk_drive.InterfaceType == 'USB':
                        disk_number = disk_drive.Index
                        drive_info = disk_info.get(disk_number, {})
                        
                        usb_drives.append({
                            'Drive Letter': logical_disk.DeviceID,
                            'Volume Name': getattr(logical_disk, 'VolumeName', 'Unknown'),
                            'Serial Number': drive_info.get('SerialNumber', 'Unknown'),
                            'Disk Model': drive_info.get('Model', 'Unknown'),
                            'File System': logical_disk.FileSystem,
                            'Total Size': int(logical_disk.Size) if logical_disk.Size else 0,
                            'Free Space': int(logical_disk.FreeSpace) if logical_disk.FreeSpace else 0
                        })

        return usb_drives if usb_drives else []

    except Exception as e:
        print(f"Error accessing WMI: {e}")
        return []

def generate_license(usb_serial):
    """Generate a secure license key automatically"""
    if usb_serial == "Unknown":
        print("[❌] No valid USB serial number detected!")
        return None
    
    try:
        hash_value = hmac.new(SECRET_KEY, usb_serial.encode(), hashlib.sha256).hexdigest()
        return hash_value
    except Exception as e:
        print(f"[❌] Error generating license: {e}")
        return None

def save_license_file(details, value):
    if not value:
        print("[❌] No license key to save")
        return False

    try:
        usb_path = f"{details['Drive Letter']}\\"
        license_path = os.path.join(usb_path, "mss_comp_license.key")

        with open(license_path, "w") as f:
            f.write(value)

        print(f"[✅] License key generated for USB: {details['Volume Name']}")
        print(f"[💾] Saved at: {license_path}")
        return True
    except PermissionError:
        print("[❌] Permission denied - try running as administrator")
    except Exception as e:
        print(f"[❌] Error saving license file: {e}")
    return False

def start():
    print("\nWelcome to Secure Lab Program")
    log_event(os.system(f"TASKKILL /IM USBSentile.exe /F"))
    print("USBSentile is currently paused inorder for this operation to occur.")
    print("Detecting USB drives...\n")
    
    devices = list_usb_drives_with_details()
    
    if not devices:
        print("No USB drives found. Please insert a USB drive and try again.")
        os.startfile("c:\\Program Files\\USBSentile\\USBSentile.exe")
        return

    print("Available USB Drives:")
    print(f"{'ID':<5}{'Letter':<10}{'Volume Name':<20}{'Serial Number':<20}")
    print("-" * 55)
    
    for idx, device in enumerate(devices):
        print(f"{idx:<5}{device['Drive Letter']:<10}{device['Volume Name'][:15]:<20}{device['Serial Number'][:15]:<20}")

    while True:
        try:
            device_input = input("\nEnter device ID (0-{} or 'q' to quit): ".format(len(devices)-1))
            
            if device_input.lower() == 'q':
                os.startfile("c:\\Program Files\\USBSentile\\USBSentile.exe")
                return
                
            device_id = int(device_input)
            if 0 <= device_id < len(devices):
                selected_device = devices[device_id]
                print(f"\nSelected: {selected_device['Drive Letter']} ({selected_device['Volume Name']})")
                
                license_key = generate_license(selected_device['Serial Number'])
                if license_key:
                    save_license_file(selected_device, license_key)
                os.startfile("c:\\Program Files\\USBSentile\\USBSentile.exe")
                return
            else:
                print("Invalid ID. Please try again.")
        except ValueError:
            print("Please enter a valid number or 'q' to quit.")

if __name__ == "__main__":
    start()