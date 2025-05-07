import hmac
import hashlib
import os
import time
from plyer import notification
import win32file
import win32con
import win32com.client
import logging
import sqlite3
import threading
import pythoncom
from typing import List, Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SECRET_KEY = b"4654365f-a510-47b4-a2b6-e2bf1993f0ef"

logging.basicConfig(
    filename="usb_sentinel.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class USBFileMonitor(FileSystemEventHandler):
    def __init__(self, usb_name, usb_serial):
        self.usb_name = usb_name
        self.usb_serial = usb_serial
    
    def on_created(self, event):
        if not event.is_directory:
            log_file_transfer(self.usb_name, self.usb_serial, event.src_path, "copied")

    def on_deleted(self, event):
        if not event.is_directory:
            log_file_transfer(self.usb_name, self.usb_serial, event.src_path, "deleted")

    def on_modified(self, event):
        if not event.is_directory:
            log_file_transfer(self.usb_name, self.usb_serial, event.src_path, "modified")

def start_usb_monitoring(usb_drive, usb_name, usb_serial):
    """Monitor a USB drive for file changes."""
    event_handler = USBFileMonitor(usb_name, usb_serial)
    observer = Observer()
    observer.schedule(event_handler, usb_drive, recursive=True)
    observer.start()
    print(f"[🔍] Monitoring {usb_drive} for file transfers...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def init_database():
    """Initialize the database for tracking file transfers."""
    conn = sqlite3.connect("usb_history.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS file_transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usb_name TEXT,
        usb_serial TEXT,
        file_path TEXT,
        action TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def log_file_transfer(usb_name, usb_serial, file_path, action):
    """Log file transfers in the database."""
    conn = sqlite3.connect("usb_history.db")
    cursor = conn.cursor()
    
    cursor.execute("""INSERT INTO file_transfers (usb_name, usb_serial, file_path, action)
                      VALUES (?, ?, ?, ?)""", (usb_name, usb_serial, file_path, action))
    
    conn.commit()
    conn.close()
    log_event(f"[📂] Logged: {file_path} - {action}")

def log_event(message: str, level="info"):
    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)

def list_usb_drives_with_details() -> List[Dict[str, str]]:
    """List all connected USB drives with detailed information"""
    try:
        pythoncom.CoInitialize()  # Initialize COM library

        wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        wmi_service = wmi.ConnectServer(".", "root\\cimv2")
        usb_drives = []

        physical_disks = wmi_service.ExecQuery("SELECT * FROM Win32_DiskDrive WHERE InterfaceType = 'USB'")
        disk_info = {}
        for disk in physical_disks:
            serial_number = getattr(disk, 'SerialNumber', '').strip()
            disk_info[disk.Index] = {'SerialNumber': serial_number if serial_number else "Unknown", 'Model': disk.Model}

        logical_disks = wmi_service.ExecQuery("SELECT * FROM Win32_LogicalDisk WHERE DriveType = 2")
        for logical_disk in logical_disks:
            partitions = wmi_service.ExecQuery(f"ASSOCIATORS OF {{Win32_LogicalDisk.DeviceID='{logical_disk.DeviceID}'}} WHERE AssocClass = Win32_LogicalDiskToPartition")
            for partition in partitions:
                disk_drives = wmi_service.ExecQuery(f"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partition.DeviceID}'}} WHERE AssocClass = Win32_DiskDriveToDiskPartition")
                for disk_drive in disk_drives:
                    if disk_drive.InterfaceType == 'USB':
                        drive_info = disk_info.get(disk_drive.Index, {})
                        usb_drives.append({
                            'Drive Letter': logical_disk.DeviceID,
                            'Volume Name': getattr(logical_disk, 'VolumeName', 'Unknown'),
                            'Serial Number': drive_info.get('SerialNumber', 'Unknown'),
                            'Disk Model': drive_info.get('Model', 'Unknown'),
                            'File System': logical_disk.FileSystem,
                            'Total Size': int(logical_disk.Size) if logical_disk.Size else 0,
                            'Free Space': int(logical_disk.FreeSpace) if logical_disk.FreeSpace else 0
                        })
        return usb_drives
    except Exception as e:
        log_event(f"[❌] Error accessing WMI: {e}", "error")
        print(f"[❌] Error accessing WMI: {e}")
        return []
    finally:
        pythoncom.CoUninitialize() # Clean up the COM library

def verify_license(usb_info: Dict[str, str]) -> bool:
    """Verify the license key on the USB drive"""
    license_path = f"{usb_info['Drive Letter']}\\mss_comp_license.key"
    try:
        if not os.path.exists(license_path):
            notification.notify(
                title="USB Alert",
                message=f"Your USB {usb_info['Volume Name']} is not authenticated. Ejecting...",
                app_name="USB Monitor",
                timeout=5  # Notification disappears after 5 seconds
            )
            return False
            
        with open(license_path, "r") as f:
            stored_hash = f.read().strip()
        
        calculated_hash = hmac.new(
            SECRET_KEY, 
            usb_info["Serial Number"].encode(), 
            hashlib.sha256
        ).hexdigest()

        return stored_hash == calculated_hash
    except Exception as e:
        notification.notify(
                title="USB Alert",
                message=f"{usb_info['Volume Name']} [⚠️] License verification error: {e}. Ejecting...",
                app_name="USB Monitor",
                timeout=5  # Notification disappears after 5 seconds
        )
        log_event(f"{usb_info['Volume Name']} [⚠️] License verification error: {e}. Ejecting...", "warning")
        return False

def eject_usb(drive_letter: str) -> bool:
    """Eject USB drive"""
    drive = f"\\\\.\\{drive_letter}"
    try:
        handle = win32file.CreateFile(
            drive,
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            0,
            None
        )
        win32file.DeviceIoControl(
            handle, 
            0x2D4808,  # IOCTL_STORAGE_EJECT_MEDIA
            None, 
            0, 
            None
        )
        win32file.CloseHandle(handle)
        log_event(f"[✅] USB {drive_letter} ejected successfully.")
        print(f"[✅] USB {drive_letter} ejected successfully.")
        return True
    except Exception as e:
        log_event(f"[❌] Error ejecting USB {drive_letter}: {e}", "error")
        print(f"[❌] Error ejecting USB {drive_letter}: {e}")
        return False

def is_usb_ejected(drive_letter: str) -> bool:
    """Check if USB drive is ejected"""
    return not os.path.exists(f"{drive_letter}\\")

def detect_usb_devices_periodically():
    """Continuously detect USB drives every 5 seconds"""
    while True:
        usb_devices = list_usb_drives_with_details()
        print("\n[📌] Detected USB Drives:")
        for device in usb_devices:
            status = "[✅ Authorized]" if verify_license(device) else "[❌ Unauthorized]"
            print(f"  {device['Drive Letter']}: {device['Volume Name']} {status}")

        # Eject unauthorized devices
        for device in usb_devices:
            if not verify_license(device):
                log_event(f"[🚨] Unauthorized USB detected: {device['Volume Name']}", "error")
                print(f"[🚨] Unauthorized USB detected: {device['Volume Name']}")
                if not eject_usb(device['Drive Letter']):
                    log_event("[⚠️] Retrying ejection...", "error")
                    print("[⚠️] Retrying ejection...")
                    time.sleep(1)
                    eject_usb(device['Drive Letter'])
        
        # Wait 5 seconds before rechecking
        time.sleep(5)

def monitor_usb_devices():
    """Main monitoring loop"""
    print("[🔍] Starting USB Monitoring Service...")
    log_event("[🔍] Starting USB Monitoring Service...")
    print("[ℹ️] Press Ctrl+C to stop monitoring")
    
    init_database()

    try:
        # Start periodic USB detection in a separate thread
        usb_detection_thread = threading.Thread(target=detect_usb_devices_periodically, daemon=True)
        usb_detection_thread.start()

        while True:
            # Get list of authenticated devices and monitor their file transfers
            usb_devices = list_usb_drives_with_details()

            threads = []
            for device in usb_devices:
                if verify_license(device):
                    t = threading.Thread(target=start_usb_monitoring, args=(device["Drive Letter"], device["Volume Name"], device["Serial Number"]))
                    threads.append(t)
                    t.start()

            # Wait for file monitoring threads to finish (optional)
            for t in threads:
                t.join()

            # Sleep 5 seconds before next iteration (periodic check)
            time.sleep(5)

    except KeyboardInterrupt:
        log_event("[🛑] Monitoring stopped by user", "error")
        print("[🛑] Monitoring stopped by user")
    except Exception as e:
        log_event(f"[💥] Critical error: {e}", "error")
        print(f"[💥] Critical error: {e}")

if __name__ == "__main__":
    monitor_usb_devices()
