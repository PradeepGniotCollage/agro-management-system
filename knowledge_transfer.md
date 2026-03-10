# Project Knowledge Transfer (KT) - Soil Monitoring System

Welcome to the **Soil Monitoring System**. Ye document aapko project ki technical architecture, core features, aur installation process samjhane ke liye banaya gaya hai.

---

## 1. Project Overview (Basic)
Ye ek Smart Soil Testing system hai jo sensors ka use karke mitti (soil) ki quality check karta hai.
- **Goal**: Kisanon (Farmers) ko unki mitti ke baare mein sahi jaankari dena, jaise ki NPK levels, moisture, aur AI ki madad se micronutrients predict karna.
- **Output**: Ye system ek detailed PDF report aur invoice generate karta hai.

---

## 2. Tech Stack
Project ko modern tools ke saath banaya gaya hai:
- **Backend Framework**: FastAPI (Python) - High performance and easy to use.
- **Database**: SQLite (Development) with SQLAlchemy ORM.
- **Migrations**: Alembic - Database changes track karne ke liye.
- **AI/ML**: Joblib & Scikit-learn - Micronutrient prediction ke liye.
- **PDF Generation**: ReportLab - Sundar aur professional reports ke liye.
- **Communication**: WhatsApp integration (planned/represented in schemas).

---

## 3. Project Structure (Folder Wise)
Codebase ko clean architecture mein divide kiya gaya hai:

- `/app`: Main application folder.
    - `/api`: API Routes (Endpoints) yahan define hain.
    - `/models`: Database tables ka structure.
    - `/schemas`: Data validation ke liye Pydantic models.
    - `/services`: Main business logic (Calculation, AI connection, PDF logic).
    - `/repositories`: Database operations logic.
    - `/ai`: AI model loading aur prediction logic.
    - `/utils`: Helper functions jaise score calculations.
    - `/core`: Global configuration (`config.py`) aur custom exceptions.
- `/migrations`: Database version control files.
- `static/`: Logos aur static assets.
- `requirements.txt`: Project ki saari dependencies.

---

## 4. Key Modules & Working

### A. Soil Testing Service (`app/services/soil_service.py`)
- Ye module sensors se data collect karta hai.
- **Median Filtering**: Agar sensors fluctuating data dete hain, to hum "Median" nikaalte hain sahi value report karne ke liye.
- **Validation**: Check karta hai ki readings physical limits ke andar hain ya nahi.

### B. AI Prediction (`app/ai/soil_ai.py`)
- Agar primary sensors (NPK, pH, EC) data dete hain, to ye system AI model (`model.joblib`) ka use karke **Micronutrients** (Zinc, Boron, Calcium, etc.) predict karta hai.
- Agar model file nahi milti, to ye gracefully "MOCK" mode mein chala jaata hai.

### C. PDF & Invoice Service
- `pdf_service.py` aur `invoice_pdf_service.py` data ko ek sundar format mein convert karte hain.
- Isme QR code generation aur professional branding (Logo) integrated hai.

---

## 5. Error Handling (`app/core/exceptions.py`)
Humne custom exceptions banaye hain taaki errors clear ho:
- `SoilMonitoringError`: General errors.
- `DatabaseError`: DB issues.
- `SensorDataError`: Agar sensors connected nahi hain.

---

## 6. How to Run (Getting Started)

1.  **Environment Setup**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Database Migration**:
    ```bash
    alembic upgrade head
    ```
4.  **Start Server**:
    ```bash
    python -m uvicorn app.main:app --reload
    ```
    Ya fir root directory mein `start.bat` file ko run karein.

---

## 8. Database Architecture (ER Diagram)
System ka database schema samajhne ke liye niche diye gaye link par click karein:
- [ER Diagram Artifact](file:///C:/Users/pj071/.gemini/antigravity/brain/a1ec4463-40e6-4f7a-9568-c106f6072b26/er_diagram.md)

---

## 9. Key Features & Workflows

### 1. Farmer Registration & Soil Testing
- Jab bhi koi naya farmer aata hai, hum unki details `farmers` table mein store karte hain.
- `soil_tests` table mein sensor ki raw values aur AI predicted values store hoti hain.

### 2. Sensor Integration (Modbus)
- Sensors (NPK, pH, EC, Moisture, Temp) Modbus RTU protocol use karte hain.
- `app/services/soil_service.py` sensors se connect karta hai aur data fetch karta hai.

### 3. AI Prediction Flow
- Input: NPK, pH, EC, Temperature, Moisture.
- Model: Scikit-learn based joblib model.
- Process: `app/ai/soil_ai.py` model load karta hai aur prediction result return karta hai.

### 4. Billing & Invoicing
- Test complete hone ke baad, ek `invoice` generate hota hai.
- `invoice_items` mein service charges mention hote hain.

---

## 10. Development Tips
- **New Feature**: Pehle `models` define karein, fir `schemas`, fir `repository`, aur end mein `service` aur `api`.
- **Testing Hardware**: `verify_hardware.py` run karke check karein ki sensors sahi se detect ho rahe hain ya nahi.

---
**Happy Coding!** Agar koi doubt ho to `app/main.py` se flow check karna shuru karein.
