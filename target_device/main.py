import logging
import asyncio
import io
import argparse
import os
import time
from datetime import datetime

import pyautogui
import requests
import sseclient
from PIL import ImageDraw, ImageFont

# Define device type

names = {"maith-laptop": "笔记本电脑", "maith-desktop": "台式电脑", "TONYs_MBP": "MBP"}


def take_screenshot(device_name):
    display_name = names.get(device_name, device_name)
    screenshot = pyautogui.screenshot()

    # Add watermark
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{device_name}_{timestamp}.png'

    draw = ImageDraw.Draw(screenshot)
    font_size = screenshot.width // 20
    font = ImageFont.truetype("SourceHanSerifSC-Regular.otf", font_size)
    text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {display_name}"
    draw.text((10, 10), text, font=font, fill='red')

    buffer = io.BytesIO()
    screenshot.save(buffer, format='PNG')
    # screenshot.save(filename, format='PNG')
    buffer.seek(0)
    return filename, buffer


def take_and_upload_screenshot(server_url, device_name, request_type='spontaneous'):

    filename, screenshot = take_screenshot(device_name)
    files = {'file': (filename, screenshot, 'image/png')}
    data = {'device': device_name, 'response_type': request_type}
    response = requests.post(server_url+'/upload', files=files, params=data)
    print(f'Screenshot uploaded with response: {response.status_code}')


async def listen_to_server(server_url, device_name):
    params = {'device': device_name}

    while True:
        response = requests.get(f'{server_url}/events', params=params, stream=True)
        client = sseclient.SSEClient(response)
        print("Listening to server events")
        try:
            for event in client.events():
                print("Got event: %s" % event)
                if event.data == 'exit':
                    print("Exit event received, exiting...")
                    quit()
                if event.data == 'take_screenshot':
                    take_and_upload_screenshot(server_url, device_name, request_type='requested')
        except requests.exceptions.ChunkedEncodingError:
            print("Connection closed, reconnecting...")
            time.sleep(3)
        except KeyboardInterrupt:
            print("Exiting...")
            quit()
        except Exception as e:
            raise e


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--device_name", required=False, default="Test", help="Name of the device")
    parser.add_argument("--server_url", required=False, default="http://127.0.0.1:8888", help="Base url of the server")

    args = parser.parse_args()

    device_name = os.getenv("DEVICE_NAME")
    server_url = os.getenv("SERVER_URL")

    if device_name is None:
        device_name = args.device_name
    if server_url is None:
        server_url = args.server_url

    print(f"Device {device_name} started")
    take_and_upload_screenshot(server_url, device_name)
    asyncio.run(listen_to_server(server_url, device_name))
