# Facial Recognition Emulator Project

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Web Interface](#web-interface)
- [Emulator Details](#emulator-details)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project is a sophisticated emulator for facial recognition terminals, specifically designed to replicate the functionality of Dahua and Hikvision devices. It serves as a powerful tool for testing, development, and demonstration purposes without the need for physical hardware.

The emulator consists of two main components:
1. A management service that controls and monitors the emulators
2. The emulator itself, which mimics the behavior of actual facial recognition terminals

## Features

- **Multi-vendor Support**: Emulates both Dahua and Hikvision facial recognition terminals
- **Web-based Management Interface**: Monitor and control emulators through an intuitive web UI
- **Real-time Status Monitoring**: Track the status of each emulator instance
- **User Synchronization**: Replicates user data and access rules from the main system
- **Event Generation**: Creates fictitious events to simulate real-world usage
- **Scalability**: Supports multiple emulator instances running simultaneously
- **Dynamic Configuration**: Easily start, stop, and reconfigure emulators on the fly

## Project Structure

The project is organized into several key components:

- `EmulatorService.py`: The main management service that oversees all emulator instances
- `facial_emulator.py`: The core emulator logic, serving as the entry point for each emulator instance
- `EmulatorDahua.py`: Dahua-specific emulation logic
- `EmulatorHikvision.py`: Hikvision-specific emulation logic

Additional supporting files and directories include:
- `scripts/`: Contains utility scripts and shared functionalities
- `templates/`: HTML templates for the web interface
- `running/`: Runtime directory for active emulator instances

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/facial-recognition-emulator.git
   cd facial-recognition-emulator
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the necessary environment variables (refer to `.env.example` for required variables)

## Usage

To start the emulator management service:

```
python EmulatorService.py
```

This will launch the web interface and prepare the system for running emulator instances.

## Web Interface

The web interface, accessible at `http://localhost:8080` (by default), provides the following functionalities:

- Dashboard overview of all emulator instances
- Start/Stop controls for individual emulators
- Bulk actions for managing multiple emulators
- Real-time status updates
- User synchronization status and statistics
- Log enablement toggles for detailed debugging

## Emulator Details

### Dahua Emulator

The Dahua emulator (`EmulatorDahua.py`) replicates the behavior of Dahua facial recognition terminals, including:

- User management API endpoints
- Event generation and reporting
- Access control rule implementation

### Hikvision Emulator

The Hikvision emulator (`EmulatorHikvision.py`) mimics Hikvision facial recognition devices, featuring:

- Hikvision-specific API structure
- Event simulation based on configured frequency
- User data synchronization

Both emulators can be fine-tuned using command-line arguments when launched through `facial_emulator.py`.

## Contributing

Contributions to the Facial Recognition Emulator project are welcome! Please follow these steps to contribute:

1. Fork the repository
2. Create a new branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

For more information or support, please open an issue in the GitHub repository.
