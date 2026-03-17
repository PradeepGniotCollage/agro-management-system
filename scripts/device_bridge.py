import argparse
import json
import os
import time
from typing import Any, Dict, Optional

import httpx
import serial


def _try_parse_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    start = text.find("{")
    if start < 0:
        return None
    for end in range(text.rfind("}") + 1, start, -1):
        if text[end - 1] != "}":
            continue
        chunk = text[start:end]
        try:
            parsed = json.loads(chunk)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


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
            parsed = _try_parse_json_from_text(raw_buffer)
            if parsed is not None:
                return parsed
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


def _post_heartbeat(
    backend_url: str,
    device_key: str,
    port: str,
    connected: bool,
    data: Optional[Dict[str, Any]],
    error: Optional[str],
    timeout_s: float,
) -> None:
    url = backend_url.rstrip("/") + "/api/v1/soil-tests/sensor-status"
    payload: Dict[str, Any] = {"connected": connected, "port": port, "data": data, "error": error}
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(url, json=payload, headers={"X-DEVICE-KEY": device_key})
        resp.raise_for_status()


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
    url = backend_url.rstrip("/") + "/api/v1/soil-tests/start"
    payload: Dict[str, Any] = {
        "farmer_name": farmer_name,
        "whatsapp_number": whatsapp_number,
        "crop_type": crop_type,
        "address": address,
        "sensor_data": sensor_data,
        "user_id": user_id,
    }

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
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    args.device_key = (args.device_key or "").strip()
    args.backend_url = (args.backend_url or "").strip()

    if not args.device_key:
        raise SystemExit("DEVICE_API_KEY missing")
    if not args.farmer_name:
        raise SystemExit("farmer_name missing")
    if not args.whatsapp_number:
        raise SystemExit("whatsapp_number missing")
    if not args.crop_type:
        raise SystemExit("crop_type missing")

    while True:
        sensor_data: Optional[Dict[str, Any]] = None
        error: Optional[str] = None
        try:
            if args.mock_json:
                sensor_data = json.loads(args.mock_json)
            else:
                sensor_data = _read_json_line_from_serial(args.port, args.baud, args.timeout)
        except Exception as e:
            error = str(e)

        connected = sensor_data is not None and error is None

        if args.dry_run:
            print(json.dumps({"connected": connected, "port": args.port, "data": sensor_data, "error": error}, ensure_ascii=False))
        else:
            _post_heartbeat(
                backend_url=args.backend_url,
                device_key=args.device_key,
                port=args.port,
                connected=connected,
                data=sensor_data,
                error=error,
                timeout_s=args.http_timeout,
            )

            if connected and sensor_data is not None:
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
