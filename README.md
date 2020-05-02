# ThunderBoard
Web-based real-time data display platform for experiment monitoring.

![Screenshot](https://user-images.githubusercontent.com/2306637/80855828-eee16580-8c76-11ea-8db9-56c0f234d418.png)

## Features

 - Based on socket connection over TCP/IP. Access and push data anywhere.
 
 - Clean and easy interface. You just need to add one line (well, actually three) in your code to make it work.
 
 - Beautiful dashboard. Powered by [Flask](https://palletsprojects.com/p/flask/), [Socket.IO](https://socket.io/) and [AdminLTE](https://adminlte.io/).
 
     - Post data to multiple boards, and move objects between boards by drag-and-drop.
     
     - Support interactive components like buttons and input boxes.
     
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

## Examples

Examples can be found in `thunder_board/examples`.

### Create a dynamic figure
```python
import time
from matplotlib.figure import Figure
import numpy as np

from thunder_board.clients import TextClient, PlotClient

def make_figure(t):
    xs = np.linspace(0, 10, 100)
    ys = np.sin(t + xs)

    fig = Figure() # We encourage you not to use pyplot, since it is not thread-safe, and also consumes a lot of resources.
    ax = fig.subplots(1, 1)
    ax.plot(xs, ys)
    ax.set_title("Test Figure t=%ds" % t)
    fig.set_tight_layout(True)

    return fig

text_sender = TextClient("Status Bar", id="status", rotate=False)
log_sender = TextClient("Log", id="log", rotate=True)
plot_sender = PlotClient("Plot", id="plot", format="png") # svg format is also available.

t = 0
while True:
    try:
        text_sender.send("Time: <strong>%ds</strong>" % t) # Yeah! HTML is supported!
        log_sender.send("Rotated log at %ds" % t)
        plot_sender.send(make_figure(t))

        time.sleep(1)
        t += 1

    except KeyboardInterrupt:
        text_sender.send("Bye.")
        text_sender.close()
        plot_sender.close()
        log_sender.close_and_discard()  # "discard" means the log window will be removed from your browser.
        exit()
```

### Create a interactive dialog
```python
import time
from matplotlib.figure import Figure
import numpy as np

from thunder_board.clients import DialogClient

dialog = DialogClient("Test Dialog", id="dialog", board="Dialog")

def say(words):
    dialog.add_text_label("my_label", "Great! You said: " + words)
    dialog.display()

def reset(arg):
    dialog.add_text_label("my_label", "I've been reset :(")
    dialog.display()

def kill(arg):
    dialog.add_text_label("my_label", "Ahh. I was killed X(")
    dialog.display()
    dialog.close()
    exit()

dialog.add_group("label_and_inputbox")
dialog.add_text_label("my_label", "What do you wanna say? Press Enter to tell me ;)", group="label_and_inputbox")
dialog.add_input_box("my_box", "Input: ", handler=say, group="label_and_inputbox")

dialog.add_group("buttons")
dialog.add_button("reset_btn", "Reset", handler=reset, group="buttons")
dialog.add_button("exit_btn", "Kill me", handler=kill, group="buttons")
dialog.display()
dialog.recv_loop()
```
