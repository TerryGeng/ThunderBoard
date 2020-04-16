# ThunderBoard
Web-based real-time data display platform for experiment monitoring.

![Screenshot](https://user-images.githubusercontent.com/2306637/79185903-cbcb4f00-7e4a-11ea-9678-24737064f02d.png)

## Features

 - Based on socket connection over TCP/IP. Access and push data anywhere.
 
 - Clean and easy interface. You just need to add one line (well, actually three) in your code to make it work.
 
 - Beautiful dashboard. Powered by [Flask](https://palletsprojects.com/p/flask/), [Socket.IO](https://socket.io/) and [AdminLTE](https://adminlte.io/).
 
     - Post data to multiple boards, and move objects between boards by drag-and-drop.
     
     - Manage your subscription at ease.

## Installation

### From the release

Download `.whl` file from [release](https://github.com/TerryGeng/ThunderBoard/releases) page.

Then run
```
pip install {the_whl_file_you_downloaded}
```

### From this repo

If you don't want to use pip, please clone this repo first, then install all dependencies manually by
```
pip install flask flask-socketio Pillow
```

## Usage

1. Run the server

After installation, start the server by simply run
```
thunderboard
```
if you installed with `pip install`. If you'd like to run from this repo directly, do
```
python3 run_server.py
```

It will listen at 0.0.0.0:2333 for data and serve a web server at http://127.0.0.1:2334.

2. Send data to the server
```
import time
import matplotlib.pyplot as plt
import numpy as np

from thunder_board import senders        # import senders

text_sender = senders.TextSender("Status Bar", rotate=False, id="status")
rotated_text_sender = senders.TextSender("Test Rotated Text", rotate=True)
plot_sender = senders.PlotSender("Test Plot")

t = 0
while True:
    try:
        text_sender.send("Experiment Status: <strong>Time %ds</strong>" % t)
        rotated_text_sender.send("Rotated log at %ds" % t)  # push data to server

        xs = np.linspace(t, t+10, 100)
        ys = np.sin(xs)
        fig = plt.figure()
        plt.plot(xs, ys)
        plt.title("Test Figure t=%ds" % t)
        plot_sender.send(fig)                               # worry-free matplotlib support

        plt.close()

        time.sleep(1)
        t += 1
    except KeyboardInterrupt:
        text_sender.send("Experiment Status: Inactive")
        text_sender.close()

        plot_sender.close_and_discard()                       # these two objects will be removed from the dashboard
        rotated_text_sender.close_and_discard()
        exit()
```
