from typing import Callable
from whisper_live.client import TranscriptionClient

import rship_sdk as rship
from rship_sdk import EmitterProxy, InstanceProxy, InstanceArgs, EmitterArgs, TargetArgs
import threading
from queue import Queue
import pyaudio

from tkinter import *
from tkinter import ttk

rship_host = "10.147.20.115"
rship_port = "5155"
machine_id = "Render001-Dev"
machine_name = "Render001-Dev"
service_id = "whisper"
service_name = "Whisper"
instance_name = "Whisper"
service_type_code = "Whisper"
color = "#4A006D"

def bootstrap_instance():
    print("Connecting to Rship at", rship_host, rship_port)

    try:
        client = rship.RshipExecClient(rship_host, rship_port)
        client.connect()

        instance =  client.add_instance(
            InstanceArgs(
                name=instance_name,
                code=service_type_code,
                service_id=service_id,
                cluster_id=None,
                machine_id=machine_id,
                color=color,
                message=None
            )
        )

        print("Rship setup completed")
        return client, instance
    except Exception as e:
        print(f"Error during rship setup: {e}")

def start_speaker(instance: InstanceProxy, name: str, source_id: int, url: str, port: int, stop_flag: threading.Event):
    speaker = instance.add_target(TargetArgs(
        name=name,
        short_id=name.lower().replace(" ", "_"),
        category="Speaker",
    ))

    currently_updating = speaker.add_emitter(
        EmitterArgs(
            name="Current",
            short_id="currently_updating",
            schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string"
                    }
                }
            },
        )
    )

    confirmed = speaker.add_emitter(
        EmitterArgs(
            name="Confirmed",
            short_id="confirmed",
            schema={
                "type": "object",
                "properties": {     
                    "messages": {
                        "type": "array", 
                        "items": {
                            "type": "string"
                        }
                    }      
                    
                }
            },
        )
    )

    run_transcription(currently_updating, confirmed, Queue(), url, port, source_id, stop_flag)

def get_input_options():
    p = pyaudio.PyAudio()

    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    mic_options = []

    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            mic_options.append(name)

    return mic_options

def add_speaker(frm: Tk.frame, instance: InstanceProxy, speaker_num: int, get_url: Callable[[], str], get_port: Callable[[], int]):

    name_var = ""
    name_entry = ttk.Entry(frm, text="Speaker Name", textvariable=name_var)

    name_lavel = ttk.Label(frm, text="Speaker Name")


    mic_selector = ttk.Combobox(frm, values=get_input_options())

    start_button = ttk.Button(frm, text="Start Speaker")

    stop_event = threading.Event()

    name_lavel.grid(column=0, row=speaker_num)
    name_entry.grid(column=1, row=speaker_num)
    mic_selector.grid(column=2, row=speaker_num)
    start_button.grid(column=3, row=speaker_num)
    active = False
    
    def on_start_clicked():
        nonlocal active
        if active:
            stop_event.set()
            active = False
            start_button.config(text="Start Speaker")
        else:
            stop_event.clear()
            active = True
            start_speaker(instance, name_entry.get(), mic_selector.current(), get_url(), get_port(), stop_event)
            start_button.config(text="Stop Speaker")

    start_button.bind("<Button-1>", lambda e: on_start_clicked())

    return stop_event


def run_gui():

    (_, instance) = bootstrap_instance()

    root = Tk()
    frm = ttk.Frame(root, padding=10)
    frm.grid()

    url = "localhost"
    server_url = ttk.Entry(frm, textvariable=url)

    speaker_num = 0

    def get_url():
        return server_url.get() 
    
    def get_port():
        return 9090
    
    add_speaker_button = ttk.Button(frm, text="Add Speaker")

    server_url.grid(column=0, row=0)
    add_speaker_button.grid(column=3, row=0)

    def on_add_speaker(e):
        nonlocal speaker_num
        speaker_num += 1
        
        add_speaker(frm, instance, speaker_num, get_url, get_port)

    add_speaker_button.bind("<Button-1>", on_add_speaker)

    root.title("Whisper Live")

    root.mainloop()



def run_transcription(
        currently_updating: EmitterProxy, 
        confirmed: EmitterProxy, 
        transcript_queue: Queue, 
        url: str, 
        port: int, 
        source: int, 
        stop_flag: threading.Event
):
    def output_callback(data):

        last = data[-1]
        confirmed_sentences = data[:-1]

        last_data = {
            "message": last
        }

        confirmed_data = {
            "messages": confirmed_sentences
        }

        print("Updating", last_data)
        print("Rest", confirmed_data)

        currently_updating.pulse(last_data)
        confirmed.pulse(confirmed_data)
        transcript_queue.put(' '.join(data))

    print("Starting Transcription Client")

    client = TranscriptionClient(
        url,
        port,
        lang="en",
        translate=False,
        model="small",
        use_vad=True,
        save_output_recording=False,                            # Only used for microphone input, False by Default
        output_recording_filename="./output_recording.wav",     # Only used for microphone input
        output_callback=output_callback,
        input_device_index=source,             
        stop_event=stop_flag                                   # Only used for microphone input, 0 by Default
    )

    print("Starting transcription")

    transcript_thread = threading.Thread(target=client)
    transcript_thread.setDaemon(True)
    transcript_thread.start()


def main():

    ui_thread = threading.Thread(target=run_gui)
    ui_thread.setDaemon(True)
    ui_thread.start()

    ui_thread.join()

    print("gathering tasks")



if __name__ == "__main__":
    main()