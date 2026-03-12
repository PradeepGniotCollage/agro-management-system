import serial
import serial.tools.list_ports
from typing import Dict, Any, List, Optional
from fastapi import BackgroundTasks
import time
import logging
import numpy as np

from app.schemas.soil_test import SoilTestCreate, SoilTestResponse
from app.repositories.soil_repository import SoilRepository
from app.ai.soil_ai import soil_ai
from app.services.fertilizer_service import FertilizerService
from app.utils.soil_calculator import evaluate_status, calculate_fertilizers, calculate_soil_score, UNIT_MAP
from app.core.exceptions import SoilMonitoringError, DatabaseError, AIModelError, SensorDataError

logger = logging.getLogger(__name__)

class SoilService:

    def __init__(self, repository: SoilRepository, farmer_repository: Any = None):
        self.repository = repository
        self.farmer_repository = farmer_repository

    async def check_sensor_connection(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Robust check: Not only checks connection to bridge but validates if 
        real JSON data is actually streaming from the hardware sensor.
        """
        from app.core.config import settings
        import json
        import time

        port = settings.SERIAL_URL or "Auto-scan"
        logger.info(f"Checking real-time sensor stream at {port} (Timeout: {timeout}s)...")
        
        # Use existing logic but with shorter timeout for quick status check
        ports = [settings.SERIAL_URL] if settings.SERIAL_URL else [p.device for p in serial.tools.list_ports.comports()]
        
        if not ports:
            return {"connected": False, "data": None, "message": "No hardware ports found."}

        for p_url in ports:
            ser = None
            try:
                ser = serial.serial_for_url(p_url, do_not_open=True)
                ser.baudrate = 115200
                ser.timeout = 1 # Quick read
                ser.open()
                
                start_check = time.time()
                raw_buffer = ""
                while (time.time() - start_check) < timeout:
                    chunk = ser.read(ser.in_waiting or 1).decode('utf-8', errors='ignore')
                    if not chunk:
                        time.sleep(0.01)
                        continue
                    
                    raw_buffer += chunk
                    if '\n' in raw_buffer:
                        lines = raw_buffer.split('\n')
                        for line in lines[:-1]:
                            line = line.strip()
                            if '{' in line and '}' in line:
                                try:
                                    s_idx = line.find('{')
                                    e_idx = line.rfind('}') + 1
                                    data = json.loads(line[s_idx:e_idx])
                                    logger.info("Sensor status: Physical hardware confirmed streaming.")
                                    return {"connected": True, "data": data, "message": "Sensor is online and streaming."}
                                except: continue
                
                logger.warning(f"Port {p_url} is open but NO DATA received. Hardware might be disconnected from Arduino.")
            except Exception as e:
                logger.error(f"Status check failed for {p_url}: {e}")
            finally:
                if ser and ser.is_open:
                    ser.close()

        return {"connected": False, "data": None, "message": "Sensor hardware not detected or not streaming JSON."}

    async def reload_sensors(self) -> bool:
        """
        Attempts to re-verify the sensor connections by triggering a scan.
        """
        logger.info("Re-scanning for sensor hardware...")
        return await self.check_sensor_connection()

    async def get_live_sensor_data(self) -> Dict[str, Any]:
        """
        Automated: Scans available COM ports or uses SERIAL_URL for live JSON data.
        """
        from app.core.config import settings
        import json
        
        # Priority 1: Use explicitly configured SERIAL_URL (e.g. for Docker)
        if settings.SERIAL_URL:
            logger.info(f"Using configured SERIAL_URL: {settings.SERIAL_URL}")
            ports = [settings.SERIAL_URL]
        else:
            # Priority 2: Auto-scan local ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
            
        if not ports:
            return {"status": "Error", "message": "No Serial (COM) ports detected. Connect the sensor."}

        logger.info(f"Scanning target ports/URLs: {ports}")
        
        for port in ports:
            ser = None
            try:
                logger.info(f"Attempting to read from {port}...")
                ser = serial.serial_for_url(port, do_not_open=True)
                ser.baudrate = 115200
                ser.timeout = 2
                ser.open()
                
                # Start reading
                start_time = time.time()
                timeout = 15.0 # Give it plenty of time for real hardware
                raw_buffer = ""
                
                logger.info(f"App connected to {port}. Monitoring stream (Max {timeout}s)...")
                
                while (time.time() - start_time) < timeout:
                    # Read byte by byte or chunk to handle split transmissions
                    chunk = ser.read(ser.in_waiting or 1).decode('utf-8', errors='ignore')
                    if not chunk:
                        time.sleep(0.01)
                        continue
                    
                    raw_buffer += chunk
                    
                    # Look for complete JSON lines (split by newline)
                    if '\n' in raw_buffer:
                        lines = raw_buffer.split('\n')
                        # Keep the last part in buffer if it's incomplete
                        raw_buffer = lines[-1]
                        
                        # Process all complete lines
                        for line in lines[:-1]:
                            line = line.strip()
                            if not line: continue
                            
                            logger.info(f"Sensor Line: {line}")
                            
                            if '{' in line and '}' in line:
                                try:
                                    s_idx = line.find('{')
                                    e_idx = line.rfind('}') + 1
                                    json_str = line[s_idx:e_idx]
                                    
                                    data = json.loads(json_str)
                                    logger.info(f"Valid Sensor JSON Parsed: {data}")
                                    return {
                                        "status": "Success",
                                        "port": port,
                                        "data": data,
                                        "timestamp": time.time()
                                    }
                                except json.JSONDecodeError:
                                    continue
                
                logger.warning(f"Sensor at {port} timed out after {timeout} seconds without valid JSON.")
                
            except Exception as e:
                logger.debug(f"Failed to connect to {port}: {e}")
            finally:
                if ser and ser.is_open:
                    ser.close()
            
        return {
            "status": "Error",
            "message": "Sensor hardware not detected. Ensure the sensor is connected and streaming JSON at 115200 baud."
        }


    async def start_test(self, user_id: int, data_in: SoilTestCreate) -> SoilTestResponse:
        """
        One-Shot Workflow: 
        1. Automatically looks up or creates a farmer.
        2. Triggers a live hardware read from the sensor.
        3. Performs AI analysis and calculations.
        4. Saves and returns the final report.
        """
        from app.utils.soil_calculator import get_median, validate_reading, evaluate_status, calculate_soil_score
        
        # Step 1: Farmer Management
        try:
            farmer_id = None
            existing_farmer = None
            farmer_name = data_in.farmer_name
            address = data_in.address
            
            if self.farmer_repository:
                existing_farmer = await self.farmer_repository.get_by_whatsapp(data_in.whatsapp_number)
                if existing_farmer:
                    farmer_id = existing_farmer.id
                    logger.info(f"Found existing farmer with ID: {farmer_id}")
                    
                    # Auto-detect name and address if not provided
                    if not farmer_name:
                        farmer_name = existing_farmer.farmer_name
                    if not address:
                        address = existing_farmer.address
                    
                    # Update address if a new one is provided
                    if data_in.address and data_in.address != existing_farmer.address:
                        await self.farmer_repository.update(existing_farmer, {"address": data_in.address})
                        logger.info(f"Updated address for existing farmer: {farmer_id}")
                        address = data_in.address
                else:
                    # If new farmer, name is required
                    if not farmer_name:
                        raise SoilMonitoringError("farmer_name is required for new farmers.")
                    
                    new_farmer_data = {
                        "farmer_name": farmer_name,
                        "whatsapp_number": data_in.whatsapp_number,
                        "address": address
                    }
                    new_farmer = await self.farmer_repository.create(new_farmer_data)
                    farmer_id = new_farmer.id
                    logger.info(f"Created new farmer with ID: {farmer_id}")
        except SoilMonitoringError:
            raise
        except Exception as e:
            logger.error(f"Farmer Management Error: {str(e)}")
            raise SoilMonitoringError(f"[Farmer] Failed to manage farmer record: {str(e)}")

        # Step 2: Trigger Live Hardware Read
        try:
            sensor_res = await self.get_live_sensor_data()
            if sensor_res["status"] != "Success":
                raise ValueError(sensor_res.get("message"))
            
            raw_sensor_data = sensor_res["data"]
            
            # --- PROMINENT REAL DATA LOG ---
            logger.info("="*60)
            logger.info(f" >>> REAL HARDWARE DATA EXTRACTED: {raw_sensor_data}")
            logger.info("="*60)
            # -------------------------------

            sensor_data = {}
            for key, value in raw_sensor_data.items():
                if isinstance(value, list):
                    processed_val = get_median(value)
                else:
                    processed_val = float(value) if value is not None else 0.0
                sensor_data[key] = validate_reading(processed_val, key)
        except Exception as e:
            logger.error(f"Sensor Read Error: {str(e)}")
            raise SoilMonitoringError(f"REAL HARDWARE ERROR: {str(e)}")

        # Step 3: AI Prediction & Analysis
        test_status = "completed"
        summary_message = "Analysis complete"
        try:
            full_data = {
                "moisture": sensor_data.get("moisture", 0.0),
                "temperature": sensor_data.get("temperature", 0.0),
                "ph": sensor_data.get("ph", 0.0),
                "ec": sensor_data.get("ec", 0.0),
                "nitrogen": sensor_data.get("nitrogen", 0.0),
                "phosphorus": sensor_data.get("phosphorus", 0.0),
                "potassium": sensor_data.get("potassium", 0.0),
                "zinc": 0.0, "boron": 0.0, "iron": 0.0, "copper": 0.0,
                "magnesium": 0.0, "manganese": 0.0, "calcium": 0.0,
                "sulphur": 0.0, "organic_carbon": 0.0
            }

            try:
                micronutrients_pred = soil_ai.predict(sensor_data)
                if micronutrients_pred is None:
                    logger.warning("AI model not available. Micronutrients will remain 0.0.")
                    test_status = "incomplete"
                    summary_message = "AI model not available"
                elif micronutrients_pred:
                    for key, val in micronutrients_pred.items():
                        full_data[key] = val
                    logger.info("AI micronutrient prediction successful")
                else:
                    logger.warning("AI prediction returned no data (model missing or error). Micronutrients will remain 0.0.")
                    test_status = "incomplete"
                    summary_message = "AI model not available"
            except Exception as ai_err:
                logger.warning(f"AI prediction failure error: {str(ai_err)}")
                test_status = "incomplete"
                summary_message = "AI model not available"

            status_summary = {k: evaluate_status(v, k) for k, v in full_data.items()}
            fertilizers_data = FertilizerService.calculate_recommendations(
                npk_data={"nitrogen": sensor_data.get("nitrogen", 0.0), "phosphorus": sensor_data.get("phosphorus", 0.0), "potassium": sensor_data.get("potassium", 0.0)},
                ph=sensor_data.get("ph", 7.0),
                ec=sensor_data.get("ec", 0.0)
            )
            score = calculate_soil_score(status_summary)
        except Exception as e:
            logger.error(f"Analysis Error: {str(e)}")
            raise SoilMonitoringError(f"[Analysis] Failed to process data: {str(e)}")

        # Step 4: Finalize Record
        try:
            db_insert_data = {
                "farmer_id": farmer_id,
                "farmer_name": farmer_name,
                "whatsapp_number": data_in.whatsapp_number,
                "crop_type": data_in.crop_type,
                "sensor_status": "Connected",
                "status": test_status,
                **full_data,
                "soil_score": score,
                "fertilizer_recommendation": fertilizers_data,
                "status_summary": status_summary,
                "summary_message": summary_message
            }
            
            db_record = await self.repository.create(user_id, db_insert_data)
            logger.info(f"One-shot soil test ({test_status}) completed for ID: {db_record.id}")
            return self._map_to_response(db_record)
        except Exception as e:
            logger.error(f"Database Save Error: {str(e)}")
            raise SoilMonitoringError(f"[Database] Failed to save report: {str(e)}")


    def _map_to_response(self, db_record: Any) -> SoilTestResponse:
        try:
            from app.utils.soil_calculator import get_ideal_range
            # Reconstruct the full data representation to build lists
            full_data = {
                "moisture": db_record.moisture,
                "temperature": db_record.temperature,
                "ph": db_record.ph,
                "ec": db_record.ec,
                "nitrogen": db_record.nitrogen,
                "phosphorus": db_record.phosphorus,
                "potassium": db_record.potassium,
                "zinc": db_record.zinc,
                "boron": db_record.boron,
                "iron": db_record.iron,
                "copper": db_record.copper,
                "magnesium": db_record.magnesium,
                "manganese": db_record.manganese,
                "calcium": db_record.calcium,
                "sulphur": db_record.sulphur,
                "organic_carbon": db_record.organic_carbon
            }

            primary_keys = ["nitrogen", "phosphorus", "potassium"]
            environmental_keys = ["moisture", "temperature", "ph", "ec"]
            primary_nutrients = []
            micronutrients_response = []
            environmental_response = []

            status_summary = db_record.status_summary or {}

            for key, val in full_data.items():
                name = "pH Value" if key == "ph" else (key.replace("_", " ").title() if key != "ec" else "EC")
                
                nutrient_obj = {
                    "name": name,
                    "value": val,
                    "unit": UNIT_MAP.get(key, ""),
                    "ideal_range": get_ideal_range(key),
                    "status": status_summary.get(key, "IDEAL")
                }
                
                if key in primary_keys:
                    primary_nutrients.append(nutrient_obj)
                elif key in environmental_keys:
                    environmental_response.append(nutrient_obj)
                else:
                    micronutrients_response.append(nutrient_obj)

            fertilizer_response = []
            if isinstance(db_record.fertilizer_recommendation, dict):
                # New format from FertilizerService
                fr = db_record.fertilizer_recommendation
                fertilizer_response = [
                    {"name": "Urea", "requirement": fr.get("urea_kg_per_acre", 0), "unit": "kg/acre"},
                    {"name": "DAP", "requirement": fr.get("dap_kg_per_acre", 0), "unit": "kg/acre"},
                    {"name": "MOP", "requirement": fr.get("mop_kg_per_acre", 0), "unit": "kg/acre"}
                ]
            else:
                # Legacy format
                fertilizer_response = [{"name": f["name"], "requirement": f["requirement"], "unit": f["unit"]} for f in db_record.fertilizer_recommendation]

            return SoilTestResponse(
                report_meta={
                    "report_id": db_record.id,
                    "farmer_id": db_record.farmer_id,
                    "created_at": db_record.created_at,
                    "farmer_name": db_record.farmer_name,
                    "whatsapp_number": db_record.whatsapp_number,
                    "crop_type": db_record.crop_type,
                    "sensor_status": db_record.sensor_status,
                    "status": db_record.status
                },
                summary={
                    "moisture": db_record.moisture,
                    "temperature": db_record.temperature,
                    "ph": db_record.ph,
                    "ec": db_record.ec,
                    "soil_score": db_record.soil_score
                },
                primary_nutrients=primary_nutrients,
                micronutrients=micronutrients_response,
                environmental_parameters=environmental_response,
                fertilizer_recommendation=fertilizer_response,
                summary_message=db_record.summary_message or "Analysis complete"
            )
        except Exception as e:
            logger.error(f"Error mapping DB record to response: {str(e)} | Record ID: {getattr(db_record, 'id', 'Unknown')}")
            raise SoilMonitoringError("Failed to process soil test report data")


    async def get_soil_test(self, test_id: int, user_id: int) -> Optional[SoilTestResponse]:
        try:
            db_record = await self.repository.get_by_id(test_id)
            if db_record and db_record.user_id == user_id:
                return self._map_to_response(db_record)
            return None
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving soil test {test_id}: {str(e)}")
            raise SoilMonitoringError("An error occurred while retrieving the soil test report")

    async def get_user_history(self, user_id: int) -> List[Any]:
        try:
            return await self.repository.get_all_by_user(user_id)
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving history for user {user_id}: {str(e)}")
            raise SoilMonitoringError("An error occurred while retrieving your test history")

    async def get_farmer_history(self, farmer_id: int) -> List[Any]:
        try:
            return await self.repository.get_all_by_farmer(farmer_id)
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving history for farmer {farmer_id}: {str(e)}")
            raise SoilMonitoringError("An error occurred while retrieving farmer test history")
