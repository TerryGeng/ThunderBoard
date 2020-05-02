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
