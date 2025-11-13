
---

# Calendly Connection Test API

This FastAPI application is designed to connect to the [Calendly API](https://calendly.com/developers), fetch event types, retrieve availability, and create scheduling links. It allows you to test and interact with the Calendly API in a structured way.

## Features

* **Test connection** to the Calendly API
* **Fetch event types** for the connected user
* **Fetch availability** for a specific event type and date range
* **Create scheduling links** for booking events

## Prerequisites

Before running this application, make sure to set up your environment:

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:

   You need to provide your Calendly API token and base URL in a `.env` file. Example:

   ```
   CALENDLY_API_TOKEN=your_api_token
   BASE_URL=https://api.calendly.com
   ```

## Running the Application

To run the application, use Uvicorn to start the FastAPI server:

```bash
uvicorn main:app --reload
```

This will start the FastAPI server on `http://localhost:8000`.

## Endpoints

### `GET /`

Simple health check endpoint to ensure the application is running.

**Response**:

```json
{
  "message": "Calendly Connection Test API is running!"
}
```

### `GET /api/test-connection`

Test the connection to Calendly API.

**Response** (Success):

```json
{
  "status": "success",
  "user": "User Name"
}
```

**Response** (Error):

```json
{
  "status": "error",
  "message": "Failed to connect to Calendly"
}
```

### `GET /api/calendly/events`

Fetch all event types for the connected Calendly user.

**Response**:

```json
{
  "collection": [
    {
      "uri": "https://api.calendly.com/event_types/123456",
      "name": "Event Type Name",
      "description": "Event Type Description"
    },
    ...
  ]
}
```

### `GET /api/calendly/availability`

Fetch availability for a specific event type within a given date range.

**Query Parameters**:

* `appointment_type`: The event type URI obtained from `/api/calendly/events`
* `start_time`: Start time in ISO format (`2025-11-14T20:00:00.000000Z`)
* `end_time`: End time in ISO format (`2025-11-20T20:00:00.000000Z`)

**Response**:

```json
{
  "collection": [
    {
      "start_time": "2025-11-14T20:00:00.000000Z",
      "end_time": "2025-11-14T20:30:00.000000Z"
    },
    ...
  ]
}
```

### `POST /api/calendly/book`

Create a new scheduling link for an event type.

**Request Body**:

```json
{
  "max_event_count": 1,
  "appointment_type": "https://api.calendly.com/event_types/d43e47ac-3c94-4f6c-8d20-e1acadf25bc6",
  "owner_type": "EventType"
}
```

**Response** (Success):

```json
{
  "uri": "https://calendly.com/your-user-name/booking-link",
  "resource": {
    "max_event_count": 1,
    "owner_type": "EventType",
    "appointment_type": "https://api.calendly.com/event_types/d43e47ac-3c94-4f6c-8d20-e1acadf25bc6"
  }
}
```

**Response** (Error):

```json
{
  "error": "Calendly returned 400",
  "details": "Invalid appointment_type"
}
```

## Error Handling

* **400 Bad Request**: If the provided parameters are invalid.
* **401 Unauthorized**: If the provided API token is invalid or missing.
* **500 Internal Server Error**: If something goes wrong when interacting with the Calendly API.

## Logging

The application uses Python's built-in `logging` module for logging. Logs will be printed to the console with information, warnings, and errors.

---
