import os
import logging
from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.exceptions import RequestValidationError
import httpx
from dotenv import load_dotenv

load_dotenv()

#logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("calendly_app")


class CalendlyClient:
    def __init__(self):
        self.base_url = os.getenv("BASE_URL")
        self.token = os.getenv("CALENDLY_API_TOKEN")
        if not self.token:
            raise ValueError("Missing Calendly API token. Please set CALENDLY_API_TOKEN in your environment.")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        self.user_uri = None
        self.user_uuid = None

    async def test_connection(self):
        """Test Calendly API connection"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/users/me", headers=self.headers)
                if response.status_code == 200:
                    user_data = response.json()
                    self.user_uri = user_data["resource"]["uri"]
                    self.user_uuid = self.user_uri.split("/")[-1]
                    logger.info(f"Connected to Calendly as: {user_data['resource']['name']}")
                    logger.debug(f"User URI: {self.user_uri}")
                    return user_data
                else:
                    logger.error(f"Calendly API returned: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                logger.error(f"Error connecting to Calendly: {e}")
                return None

    async def get_event_types(self):
        """Fetch user's event types from Calendly"""
        async with httpx.AsyncClient() as client:
            try:
                # Ensure we have user info
                if not self.user_uri:
                    await self.test_connection()

                user_param = self.user_uri
                logger.info(f"Fetching event types for user: {user_param}")

                response = await client.get(
                    f"{self.base_url}/event_types",
                    headers=self.headers,
                    params={"user": user_param}
                )

                if response.status_code == 200:
                    data = response.json()
                    count = len(data.get('collection', []))
                    logger.info(f"Found {count} event types")
                    return data
                else:
                    logger.error(f"Event types API returned: {response.status_code} - {response.text}")
                    return {"error": f"Calendly returned {response.status_code}", "details": response.text}

            except Exception as e:
                logger.exception("Error fetching event types")
                return {"error": str(e)}

    async def get_availability(self, event_type_uri: str, start_time: str, end_time: str):
        """Fetch available times for a specific event type and date range"""
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Fetching availability for: {event_type_uri}")
                logger.debug(f"Date Range: {start_time} → {end_time}")

                response = await client.get(
                    f"{self.base_url}/event_type_available_times",
                    headers=self.headers,
                    params={
                        "event_type": event_type_uri,
                        "start_time": start_time,
                        "end_time": end_time
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    count = len(data.get('collection', []))
                    logger.info(f"Found {count} available time slots")
                    return data
                else:
                    logger.error(f"Availability API returned: {response.status_code} - {response.text}")
                    return {"error": f"Calendly returned {response.status_code}", "details": response.text}

            except Exception as e:
                logger.exception("Error fetching availability")
                return {"error": str(e)}


app = FastAPI(title="Calendly Connection Test API", version="1.2.0")
calendly_client = CalendlyClient()


@app.on_event("startup")
async def startup_event():
    """Run Calendly connection test on startup"""
    logger.info("Starting Calendly Connection Test...")
    await calendly_client.test_connection()


@app.get("/")
async def root():
    """Simple health check endpoint"""
    return {"message": "Calendly Connection Test API is running!"}


@app.get("/api/test-connection")
async def test_calendly_connection():
    """Trigger a Calendly API test manually"""
    result = await calendly_client.test_connection()
    if result:
        return {"status": "success", "user": result["resource"]["name"]}
    return {"status": "error", "message": "Failed to connect to Calendly"}


@app.get("/api/calendly/events")
async def get_calendly_events():
    """Fetch all Calendly event types for the connected user"""
    result = await calendly_client.get_event_types()
    return result


@app.get("/api/calendly/availability")
async def get_calendly_availability(
    appointment_type: str = Query(..., description="Calendly event type URI (from /api/calendly/events)"),
    start_time: str = Query(..., description="Start time in ISO format, e.g. 2025-11-14T20:00:00.000000Z"),
    end_time: str = Query(..., description="End time in ISO format, e.g. 2025-11-20T20:00:00.000000Z")
):
    """Fetch availability for a specific event type."""
    if not appointment_type.startswith("https://api.calendly.com/event_types/"):
        raise RequestValidationError([
            {
                "loc": ["query", "appointment_type"],
                "msg": "Invalid appointment_type. Please provide a valid appointment_type, You can get this from URI key in /api/calendly/events",
                "type": "value_error.invalid_appointment_type"
            }
        ])

    result = await calendly_client.get_availability(appointment_type, start_time, end_time)
    return result


@app.post("/api/calendly/book")
async def create_scheduling_link(
    payload: dict = Body(
        example={
            "max_event_count": 1,
            "appointment_type": "https://api.calendly.com/event_types/d43e47ac-3c94-4f6c-8d20-e1acadf25bc6",
            "owner_type": "EventType"
        }
    )
):
    """Create a new Calendly Scheduling Link (accepts appointment_type in payload)."""
    appointment_type = payload.get("appointment_type")

    if not appointment_type or not appointment_type.startswith("https://api.calendly.com/"):
        raise RequestValidationError([
            {
                "loc": ["body", "appointment_type"],
                "msg": "Invalid appointment_type. Please provide a valid event type URI.",
                "type": "value_error.invalid_appointment_type"
            }
        ])

    # Translate appointment_type -> owner
    calendly_payload = {
        "max_event_count": payload.get("max_event_count", 1),
        "owner": appointment_type,
        "owner_type": payload.get("owner_type", "EventType")
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{calendly_client.base_url}/scheduling_links",
                headers=calendly_client.headers,
                json=calendly_payload
            )

            if response.status_code == 201:
                data = response.json()
                logger.info("Scheduling link created successfully.")
                return data
            else:
                logger.error(f"Calendly returned {response.status_code}: {response.text}")
                return {
                    "error": f"Calendly returned {response.status_code}",
                    "details": response.text
                }

        except Exception as e:
            logger.exception("Error creating scheduling link")
            raise HTTPException(status_code=500, detail=f"Error creating scheduling link: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
