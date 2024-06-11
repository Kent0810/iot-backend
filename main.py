# Backend (Python)

import sys, asyncio, json, os
from fastapi import FastAPI, WebSocket, Request, responses, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from Adafruit_IO import Client, Feed, MQTTClient, Data
from dotenv import load_dotenv

# FastAPI app
app = FastAPI()

origins = [
    "http://localhost:3000",  # Replace with your frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

load_dotenv()
my_env_var = os.getenv("MY_ENV_VAR")


AIO_CHART_FEED_ID = ["temperature", "humidity"]

AIO_SCHED_FEED_ID = ["schedules"]

# Getting Latest Value
mqttClient = MQTTClient(ADAFRUIT_IO_USERNAME , ADAFRUIT_IO_KEY)
# Get All Value
aio = Client(ADAFRUIT_IO_USERNAME , ADAFRUIT_IO_KEY)

feed_data = {feed_id: False for feed_id in AIO_CHART_FEED_ID + AIO_SCHED_FEED_ID}

def on_connect(client):
    print("Connected...")
    for id in AIO_CHART_FEED_ID + AIO_SCHED_FEED_ID:
        client.subscribe(id)

def on_subscribe(client , userdata , mid , granted_qos):
    print("Subscribed...")

def on_disconnect(client):
    print("Disconnected...")
    sys.exit (1)

def on_message(client , feed_id , payload):
    global feed_data
    feed_data[feed_id] = True
    print("Data is from: " + feed_id + ", Payload: " + payload)

mqttClient.on_connect = on_connect
mqttClient.on_disconnect = on_disconnect
mqttClient.on_message = on_message
mqttClient.on_subscribe = on_subscribe

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WS Connected")
    
    try:
        while True:
            response = {}
            for feed_id in AIO_CHART_FEED_ID + AIO_SCHED_FEED_ID:
                if feed_data[feed_id]:
                    if feed_id in AIO_CHART_FEED_ID:
                        response[feed_id] = aio.receive(feed_id).value
                    elif feed_id in AIO_SCHED_FEED_ID:
                        response[feed_id] = aio.receive(feed_id).value
                    feed_data[feed_id] = False
            if response:
                await websocket.send_json(response)
                
            print(response)
            await asyncio.sleep(2)
        
    except WebSocketDisconnect:
        print("WebSocket connection closed")
        
@app.get("/latest-data")
def get_latest_data():
    data={}
    for feed_id in AIO_CHART_FEED_ID + AIO_SCHED_FEED_ID:
        data[feed_id] = aio.receive(feed_id).value
    print(data)
    return data

@app.get("/chart-data")
def get_chart_data():    
    data = {}
    for feed_id in AIO_CHART_FEED_ID:
        data[feed_id] = [d.value for d in aio.data(feed_id)]
    return data

@app.post("/scheduler")
async def post_scheduler(request: Request):
    try:
        scheduler = await request.json()
        print(scheduler)
        scheduler_in_string = json.dumps(scheduler)
        aio.create_data("schedules", Data(value=scheduler_in_string))
        return {"message": "Scheduler data saved successfully"}
    except Exception as e:
        error_message = f"An error occurred while processing the request: {str(e)}"
        return responses.JSONResponse(content={"error": error_message}, status_code=500)
    
if __name__ == "__main__":
    try:            
        mqttClient.connect()
    except Exception as e:
        print('could not connect to MQTT server {}{}'.format(type(e).__name__, e))
        sys.exit()
    mqttClient.loop_background()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)