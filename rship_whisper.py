import asyncio
from typing import Callable
from whisper_live.client import TranscriptionClient

import rship_sdk as rship
from rship_sdk import EmitterProxy, InstanceProxy, InstanceArgs, EmitterArgs, TargetArgs
import threading
from queue import Queue, Empty
import pyaudio

from tkinter import *
from tkinter import ttk
from customtkinter import *

from PIL import Image, ImageTk
import os

rship_host = "10.147.20.115"
rship_port = "5155"
machine_id = "Render001-Dev"
machine_name = "Render001-Dev"
service_id = "whisper"
service_name = "Whisper"
instance_name = "Whisper"
service_type_code = "Whisper"
color = "#4A006D"

async def bootstrap_instance():
    print("Connecting to Rship at", rship_host, rship_port)

    try:
        client = rship.RshipExecClient(rship_host, rship_port)
        await client.connect()

        instance = await client.add_instance(
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

async def start_speaker(instance: InstanceProxy, name: str, source_id: int, url: str, port: int, stop_flag: threading.Event):
    speaker = await instance.add_target(TargetArgs(
        name=name,
        short_id=name.lower().replace(" ", "_"),
        category="Speaker",
    ))

    currently_updating = await speaker.add_emitter(
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

    confirmed = await speaker.add_emitter(
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

    transcript_queue = Queue()

    run_transcription(currently_updating, confirmed, transcript_queue, url, port, source_id, stop_flag)

    return transcript_queue

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

def add_speaker( instance: InstanceProxy, config_frame: CTkFrame, transcript_frame: CTkFrame, speaker_num: int, get_url: Callable[[], str], get_port: Callable[[], int]):
    font = CTkFont(family="Monospace", size=12, weight="bold")

    row_offset = speaker_num * 2 + 2

    name_label = CTkLabel(config_frame, font=font, text="Speaker Name").grid(column=0, row=row_offset, sticky="wn", padx=(0, 2))
    name_var = StringVar(value="Speaker")
    name_entry = CTkEntry(config_frame, textvariable=name_var)
    name_entry.grid(column=1, row=row_offset, sticky="we", padx=(0, 1), pady=(0, 1))

    audio_label = CTkLabel(config_frame, font=font, text="Audio Source").grid(column=0, row=row_offset + 1, sticky="wn")
    audio_selector = CTkComboBox(config_frame, values=get_input_options(), state="readonly", width=100)
    audio_selector.grid(column=1, row=row_offset + 1, columnspan=2, sticky="we", pady=(0, 8))

    start_button = CTkButton(config_frame, font=font, text="Start Transcription")
    start_button.grid(column=2, row=row_offset, sticky="we", pady=(0, 1))

    stop_event = threading.Event()
    active = False
    
    async def on_start_clicked():
        nonlocal active
        if active:
            stop_event.set()
            active = False
            start_button.configure(text="Start Transcription")
        else:
            stop_event.clear()
            active = True
            selected_index = audio_selector.get()
            selected_source_id = get_input_options().index(selected_index)
            transcript_queue = await start_speaker(instance, name_entry.get(), selected_source_id, get_url(), get_port(), stop_event)
            start_button.configure(text="Stop Transcription")
            print("Transcription started")
            print_transcript(transcript_frame, transcript_queue)

    def on_button_click(e):
        loop = asyncio.get_event_loop()
        asyncio.run(on_start_clicked())

    start_button.bind("<Button-1>", on_button_click)

    return stop_event

def print_transcript(frm: CTkFrame, transcript_queue: Queue):

    transcript_content = CTkTextbox(frm, wrap="word")
    transcript_content.grid(column=0, row=1, sticky="nsew")
    transcript_content.configure(state=DISABLED)  # Make the text widget read-only

    def update_transcript():
        try:
            transcript = transcript_queue.get_nowait()
            transcript_formatted = transcript.replace("\n", " ")
            transcript_content.configure(state=NORMAL)
            transcript_content.delete(1.0, END)
            transcript_content.insert(END, transcript_formatted)
            transcript_content.configure(state=DISABLED)
        except Empty:
            pass
        finally:
            frm.after(100, update_transcript)

    update_transcript()

def run_gui():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client, instance = loop.run_until_complete(bootstrap_instance())
    loop.close()

    if client and instance:
        run_gui_sync(client, instance)
    else:
        print("Failed to setup rship")

def run_gui_sync(client, instance):
    app = CTk()
    app.geometry("400x600")
    app._set_appearance_mode("dark")
    app.title("rship-whisper")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "rocketship.ico")
    icon = ImageTk.PhotoImage(file=icon_path)

    app.wm_iconbitmap()
    app.iconphoto(True, icon)

    font = CTkFont(family="Monospace", size=12, weight="bold")

    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure((0, 1), weight=1)

    config_frame = CTkScrollableFrame(app)
    config_frame.grid(row=0, column=0, sticky="nswe")

    url_label = CTkLabel(config_frame, text="Whisper Server", font=font, fg_color="#4A006D", width=90).grid(column=0, row=0, sticky="wn", padx=(0, 5))
    url_var = StringVar(value="localhost")
    server_url = CTkEntry(config_frame, textvariable=url_var)
    server_url.grid(column=1, row=0, sticky="we", padx=(0, 2), pady=(0, 5))

    add_speaker_button = CTkButton(master=config_frame, font=font, text="Add Speaker", corner_radius=4, fg_color="#3C3C3C", hover_color="#646464")
    add_speaker_button.grid(row=0, column=2, sticky="w", pady=(0, 5))

    separator = CTkFrame(config_frame, height=3, border_color="white", border_width=1)
    separator.grid(row=1, column=0, columnspan=3, sticky="we", pady=(0, 2))
    
    transcript_frame = CTkFrame(app)    
    transcript_frame.grid(row=1, column=0, sticky="nsew")

    app.grid_rowconfigure(0, weight=100)
    transcript_frame.grid_rowconfigure(0, weight=100)
    transcript_frame.grid_columnconfigure(0, weight=100)

    speaker_num = 0

    def get_url():
        return server_url.get() 
    
    def get_port():
        return 9090

    def on_add_speaker(e):
        nonlocal speaker_num
        speaker_num += 1
        
        add_speaker(instance, config_frame, transcript_frame, speaker_num, get_url, get_port)

    add_speaker_button.bind("<Button-1>", on_add_speaker)

    app.mainloop()



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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ui_thread = threading.Thread(target=run_gui, daemon=True)
    ui_thread.start()

    ui_thread.join()

    print("gathering tasks")



if __name__ == "__main__":
    main()