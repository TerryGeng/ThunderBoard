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

import senders

text_sender = senders.TextSender("Test Text", rotate=False)
plot_sender = senders.PlotSender("Test Plot")

t = 0
while True:
    text_sender.send("Time %ds" % t)
    
    xs = np.linspace(t, t+10, 100)
    ys = np.sin(xs)
    fig = plt.figure()
    plt.plot(xs, ys)
    plt.title("Test Figure t=%ds" % t)
    
    plot_sender.send(fig)

    plt.close()

    time.sleep(1)
    t += 1

```
