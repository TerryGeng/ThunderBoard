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
