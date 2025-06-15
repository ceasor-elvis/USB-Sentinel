# USB-Sentinel

USB-Sentinel is a security-focused tool for controlling and monitoring USB access on Windows computers, designed for use in schools and workplaces.

## Features

- **USB Authorization:** Only USB drives with a valid license key can be used.
- **Automatic Ejection:** Unauthorized USB drives are automatically ejected.
- **File Activity Logging:** All file transfers (copy, delete, modify) on authorized USB drives are logged.
- **Admin Tool:** Easily generate and save license keys for USB drives.
- **Notifications:** Users are notified when unauthorized USBs are detected or ejected.
- **Persistent Logging:** Events are logged to a file for auditing.
- **SQLite Database:** File transfer history is stored in a local database.
- **Executable:** Includes a Windows executable `USBSentile.exe` (currently functional but may still contain some bugs).


## Project Structure

- [`main.py`](main.py): Main monitoring service. Detects USB drives, verifies licenses, logs file activity, and handles ejection of unauthorized devices.
- [`admin.py`](admin.py): Admin utility for generating and saving license keys to USB drives.
- `USBSentile.exe`: Windows executable version of the monitoring service (works, but still has some bugs to solve).

---

## Usage

### 1. Admin: Register a USB Drive

Run the admin tool to generate and save a license key to a USB drive:

```sh
python admin.py
```

- The tool will list all connected USB drives.
- Select the drive you want to authorize.
- A license key will be generated and saved to the USB drive as `mss_comp_license.key`.

### 2. Start Monitoring

Run the monitoring service:

```sh
python main.py
```

- The service will continuously monitor for USB drives.
- Only authorized drives (with a valid license key) will be allowed.
- Unauthorized drives will be ejected and logged.
- File activity on authorized drives will be logged to a local database and log file.


Or use the executable (note: some bugs may still exist):

```sh
USBSentile.exe
```

- The service will continuously monitor for USB drives.
- Only authorized drives (with a valid license key) will be allowed.
- Unauthorized drives will be ejected and logged.
- File activity on authorized drives will be logged to a local database and log file.

---


## Requirements

- Windows OS
- Python 3.x
- Dependencies:
  - `pywin32`
  - `plyer`
  - `watchdog`

Install dependencies with:

```sh
pip install pywin32 plyer watchdog
```

## Log and Data Storage

- Logs and database are stored in:  
  `%USERPROFILE%\.usbsentile\`

## License

This project is for educational and internal use only.

---

For more details, see the code in [`main.py`](main.py) and [`admin.py`](admin.py).
