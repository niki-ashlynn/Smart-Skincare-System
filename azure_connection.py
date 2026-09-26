import json
import os
from azure.iot.device import IoTHubDeviceClient, Message


# configuration ---------------------------------------------

CONNECTION_STRING = os.getenv(
    "AZURE_IOT_HUB_CONNECTION_STRING",
    " "
)

client = None
azure_connected = False


# connect to azure ---------------------------------------------

def connect_azure():
    global client, azure_connected

    if not CONNECTION_STRING:
        print(
            "azure iot hub disabled: connection string is not set"
        )
        return False

    try:
        client = IoTHubDeviceClient.create_from_connection_string(
            CONNECTION_STRING
        )
        client.connect()
        azure_connected = True
        print("connected to azure iot hub")
        return True

    except Exception as error:
        azure_connected = False
        print(
            "azure connection failed:",
            error
        )
        return False


# send inventory data ---------------------------------------------

def send_inventory_update(product):
    if not azure_connected or client is None:
        return False

    try:
        data = {
            "product_id": product.get("id"),
            "barcode": product.get("barcode"),
            "brand": product.get("brand"),
            "name": product.get("name"),
            "category": product.get("category"),
            "batch_code": product.get("batch_code"),
            "expiry_date": product.get("expiry_date"),
            "remaining": product.get("remaining"),
            "status": product.get("status"),
            "stock_status": product.get("stock_status")
        }

        message = Message(
            json.dumps(data)
        )
        message.content_type = "application/json"
        message.content_encoding = "utf-8"

        client.send_message(
            message
        )

        return True

    except Exception as error:
        print(
            "failed to send inventory update:",
            error
        )
        return False


# disconnect from azure ---------------------------------------------

def disconnect_azure():
    global client, azure_connected

    try:
        if client is not None and azure_connected:
            client.disconnect()

    except Exception:
        pass

    client = None
    azure_connected = False
