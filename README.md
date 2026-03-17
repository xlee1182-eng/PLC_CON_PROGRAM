# PLC Communication Program

## 📌 Project Description
This project is a Python-based PLC communication system.

## 🛠 Tech Stack
- Python 3.x
- Snap7 / OPC
- AsyncIO
- Oracle / PostgreSQL

## 📂 Project Structure
```
src/
  drivers/
  jobs/
  main.py
requirements.txt
```

## 🚀 Installation

```bash
git clone https://github.com/your_id/your_repo.git
cd your_repo
pip install -r requirements.txt
```

## ▶ Run

```bash
python main.py
```

## 👤 Author
LI XIONG

## PLC Driver Integration

The project now uses a unified driver factory.

- Driver factory file: app/plc_drivers/driver_factory.py
- PLC runtime build point: app/jobs/plcjob.py

When adding a new PLC protocol:

1. Implement a new async driver class based on BaseAsyncPLC.
2. Add a builder function in app/plc_drivers/driver_factory.py.
3. Register the type in DRIVER_BUILDERS.

No additional type-branching changes are required in plcjob.
