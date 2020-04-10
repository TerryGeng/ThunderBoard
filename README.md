# ThunderBoard
Web-based real-time data display platform for experiment monitoring.

![image](https://user-images.githubusercontent.com/2306637/78978303-1e0b2800-7b4c-11ea-93ec-a30739e17e44.png)

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
