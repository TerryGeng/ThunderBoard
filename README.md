# ThunderBoard
Web-based real-time data display platform for experiment monitoring.

![Screenshot](https://user-images.githubusercontent.com/2306637/79185903-cbcb4f00-7e4a-11ea-9678-24737064f02d.png)

## Features

 - Based on socket connection over TCP/IP. Access and push data anywhere.
 
 - Clean and easy interface. You just need to add one line (well, actually three) in your code to make it work.
 
 - Beautiful dashboard. Powered by [Flask](https://palletsprojects.com/p/flask/), [Socket.IO](https://socket.io/) and [AdminLTE](https://adminlte.io/).
 
     - Post data to multiple boards, and move objects between boards by drag-and-drop.
     
     - Manage your subscription at ease.

## Dependecies

```
pip install flask flask-socketio Pillow
```

## Usage

1. Run the server
```
python3 server.py
```

It will listen at 0.0.0.0:2333 for data and serve a web server at http://127.0.0.1:2334.

2. Send data to the server
```
import time
import matplotlib.pyplot as plt
import numpy as np

import senders        # import senders

text_sender = senders.TextSender("Test Text", rotate=False)
rotated_text_sender = senders.TextSender("Test Rotated Text", rotate=True)
plot_sender = senders.PlotSender("Test Plot")

t = 0
while True:
    try:
        xs = np.linspace(t, t+10, 100)
        ys = np.sin(xs)
        text_sender.send("Time %ds" % t)         # push data to the server, 127.0.0.1:2333 by default
        rotated_text_sender.send("Rotated log at %ds" % t)
        fig = plt.figure()
        plt.plot(xs, ys)
        plt.title("Test Figure t=%ds" % t)
        plot_sender.send(fig)                    # worry-free matplotlib support

        plt.close()

        time.sleep(1)
        t += 1
        
    except KeyboardInterrupt:
        text_sender.close_and_discard()         # remove objects from the dashboard when exiting
        plot_sender.close_and_discard()
        rotated_text_sender.close_and_discard()
        exit()

```
