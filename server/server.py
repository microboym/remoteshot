import asyncio
import os

import tornado.escape
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket

root = os.getenv("IMAGE_DIR", "./Pictures")


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class ScreenShotController(object):
    class ScreenShotDevice(object):
        def __init__(self, dev_name, handler):
            self.dev_name = dev_name
            self.handler = handler
            self.buffer = asyncio.Queue()

        async def get_screenshot(self):
            print("Getting screenshot from ", self.dev_name)
            await self.handler.take_screenshot()
            return await self.buffer.get()

    def __init__(self):
        self.devices = dict()

    def add_device(self, dev_name, handler):
        if dev_name in self.devices:
            self.devices[dev_name].handler.close()
        self.devices[dev_name] = ScreenShotController.ScreenShotDevice(dev_name, handler)

    def remvoe_device(self, dev_name):
        self.devices[dev_name].buffer.put_nowait(None)
        self.devices.pop(dev_name)

    async def request_screenshot(self):
        tasks = [device.get_screenshot() for device in self.devices.values()]
        filenames = await asyncio.gather(*tasks, return_exceptions=True)
        filenames = [f for f in filenames if f is not None and not isinstance(f, Exception)]
        return filenames

    def add_screenshot(self, device_name, filename):
        print("Adding screenshot", device_name, filename)
        self.devices[device_name].buffer.put_nowait(filename)


controller = ScreenShotController()


class UploadHandler(tornado.web.RequestHandler):
    def post(self):
        # Get device name
        dev_name = self.get_argument("device", None)
        response_type = self.get_argument("response_type", None)

        # Fetch the file
        file1 = self.request.files['file'][0]
        filename = file1['filename']
        save_path = os.path.join(root, filename)
        with open(save_path, 'wb') as f:
            f.write(file1['body'])
        print(f"File {filename} saved, device: {dev_name}, response_type: {response_type}")
        self.write({'status': 'success', 'filename': filename})

        if response_type == 'requested':
            controller.add_screenshot(dev_name, filename)
        self.finish()


class TargetDeviceHandler(tornado.web.RequestHandler):
    def initialize(self):
        self._auto_finish = False

    def set_default_headers(self):
        self.set_header('Content-Type', "text/event-stream")
        self.set_header('Content-Control', "no-cache")
        self.set_header('Connection', "keep-alive")
        self.set_header('Access-Control-Allow-Origin', "*")
        self.set_header('X-Accel-Buffering', "no")

    async def get(self):
        self.dev_name = self.get_argument("device", None)
        print(f"Device {self.dev_name} connected")
        controller.add_device(self.dev_name, self)
        await self.flush()

    def on_connection_close(self):
        print(f"Device {self.dev_name} disconnected")
        controller.remvoe_device(self.dev_name)

    async def take_screenshot(self):
        self.write("data: take_screenshot\n\n")
        await self.flush()

    def close(self):
        self.write("data: exit\n\n")
        self.finish()


class FetchScreenshotHandler(tornado.web.RequestHandler):
    async def get(self):
        filenames = await controller.request_screenshot()
        self.write({'status': 'success', 'filenames': filenames})
        await self.finish()


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/events", TargetDeviceHandler),
        (r"/fetch", FetchScreenshotHandler),
        (r"/upload", UploadHandler),
        (r"/images/(.*)", tornado.web.StaticFileHandler, {"path": root}),
    ])


async def main():
    app = make_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(8888)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
