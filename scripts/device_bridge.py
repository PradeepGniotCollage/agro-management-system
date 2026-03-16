import argparse
import json
import os
import time
from typing import Any, Dict, Optional

import httpx
import serial


def _read_json_line_from_serial(port: str, baud: int, timeout_s: float) -> Dict[str, Any]:
    ser = serial.serial_for_url(port, do_not_open=True)
    ser.baudrate = baud
    ser.timeout = 1
    ser.open()
    try:
        start = time.time()
        raw_buffer = ""
        while time.time() - start < timeout_s:
            chunk = ser.read(ser.in_waiting or 1).decode("utf-8", errors="ignore")
            if not chunk:
                time.sleep(0.01)
                continue

            raw_buffer += chunk
            if "\n" not in raw_buffer:
                continue

            lines = raw_buffer.split("\n")
            raw_buffer = lines[-1]
            for line in lines[:-1]:
                line = line.strip()
                if not line:
                    continue
                if "{" not in line or "}" not in line:
                    continue
                s_idx = line.find("{")
                e_idx = line.rfind("}") + 1
                return json.loads(line[s_idx:e_idx])

        raise TimeoutError(f"No valid JSON received within {timeout_s} seconds from {port}")
    finally:
        if ser.is_open:
            ser.close()


def _post_ingest(
    backend_url: str,
    device_key: str,
    farmer_name: str,
    whatsapp_number: str,
    crop_type: str,
    address: Optional[str],
    sensor_data: Dict[str, Any],
    user_id: Optional[int],
    timeout_s: float,
) -> Dict[str, Any]:
    url = backend_url.rstrip("/") + "/api/v1/soil-tests/ingest"
    payload: Dict[str, Any] = {
        "farmer_name": farmer_name,
        "whatsapp_number": whatsapp_number,
        "crop_type": crop_type,
        "address": address,
        "sensor_data": sensor_data,
    }
    if user_id is not None:
        payload["user_id"] = user_id

    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(url, json=payload, headers={"X-DEVICE-KEY": device_key})
        resp.raise_for_status()
        return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default=os.getenv("BACKEND_URL", "http://localhost:8000"))
    parser.add_argument("--device-key", default=os.getenv("DEVICE_API_KEY", ""))
    parser.add_argument("--user-id", type=int, default=int(os.getenv("DEVICE_USER_ID", "0")) or None)
    parser.add_argument("--port", default=os.getenv("SERIAL_PORT", "COM3"))
    parser.add_argument("--baud", type=int, default=int(os.getenv("SERIAL_BAUD", "115200")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("SERIAL_TIMEOUT", "30")))
    parser.add_argument("--http-timeout", type=float, default=float(os.getenv("HTTP_TIMEOUT", "30")))
    parser.add_argument("--farmer-name", default=os.getenv("FARMER_NAME", ""))
    parser.add_argument("--whatsapp-number", default=os.getenv("WHATSAPP_NUMBER", ""))
    parser.add_argument("--crop-type", default=os.getenv("CROP_TYPE", ""))
    parser.add_argument("--address", default=os.getenv("ADDRESS"))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--mock-json", default=os.getenv("MOCK_SENSOR_JSON", ""))
    args = parser.parse_args()

    if not args.device_key:
        raise SystemExit("DEVICE_API_KEY missing")
    if not args.farmer_name:
        raise SystemExit("farmer_name missing")
    if not args.whatsapp_number:
        raise SystemExit("whatsapp_number missing")
    if not args.crop_type:
        raise SystemExit("crop_type missing")

    while True:
        if args.mock_json:
            sensor_data = json.loads(args.mock_json)
        else:
            sensor_data = _read_json_line_from_serial(args.port, args.baud, args.timeout)

        result = _post_ingest(
            backend_url=args.backend_url,
            device_key=args.device_key,
            farmer_name=args.farmer_name,
            whatsapp_number=args.whatsapp_number,
            crop_type=args.crop_type,
            address=args.address,
            sensor_data=sensor_data,
            user_id=args.user_id,
            timeout_s=args.http_timeout,
        )
        print(json.dumps(result, ensure_ascii=False))

        if args.once:
            break
        time.sleep(1)


if __name__ == "__main__":
    main()
