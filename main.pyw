#TODO:
#save state
#More efficient
#Rename vars
#Random thoughts:
#Multiproccesing on chunk loading in python minecraft clone

#IMPORTANT
#VSCode crashes after a day of running. I you want to run it indefinetly run it from a terminal.

from ipaddress import ip_address
from time import sleep, time
from sys import stdout

class InUrlBlocklist(Exception):
    def __init__(self, url, message="The current url is in the blocklist"):
        self.url = url
        self.message = message + f" ({self.url})"
        super().__init__(self.message)

def log(*values: object, log_list: object = None, seperator: str = " ", end: str = "\n", flush: bool = True):
    if log_list:
        log_list.append(seperator.join(map(str, values)) + end)

    try:
        stdout.write(seperator.join(map(str, values)) + end)
        if flush: stdout.flush()
    except:
        pass

def finder(range_min, range_max, bad_urls, manager_dict, server_dict, log_list, default_icon):
    from mcstatus import MinecraftServer
    from datetime import datetime
    from random import randint, random

    def found(ip, status, server_dict, manager_dict, default_icon):
        ip_line = f"IP: {ip}"
        description_line = "".join(['DESCRIPTION: "', status.description.replace("\n", ", "), '"'])
        ping_line =  f"PING: {status.latency} ms"
        version_line = f"VERSION: {status.version.name}"
        players_line = f"PLAYERS: {status.players.online}/{status.players.max}" + (f", [{', '.join([player.name for player in status.players.sample])}]" if not type(status.players.sample) == type(None) else "")

        message = "\n".join([
            f"====FIND ({datetime.now().strftime('%d/%m/%Y, %I:%M:%S %p')})====",
            ip_line,
            description_line,
            ping_line,
            version_line,
            players_line
        ]) + "\n"
        with open("finds.txt", "a") as out: out.write(message)

        server_dict["ip"] = ip_line
        server_dict["description"] = description_line
        server_dict["ping"] = ping_line
        server_dict["version"] = version_line
        server_dict["players"] = players_line

        if type(status.favicon) == type(None): server_dict["icon"] = default_icon
        else: server_dict["icon"] = status.favicon

        server_dict["update"] = True
        manager_dict["total_found"] += 1

    tries = 3

    for ip_number in range(range_min, range_max):
        while not manager_dict["awake"]:
            sleep(randint(1, 5) + round(random() * 100) / 100)

        ip = str(ip_address(ip_number))
        out_string = f"{ip}"

        try:
            if ip in bad_urls:
                raise InUrlBlocklist(ip)

            server = MinecraftServer.lookup(ip)

            for current_try in range(tries):
                try:
                    status = server.status(tries=1)
                    
                    if status:
                        break
                except OSError as e:
                    if current_try + 1 < tries and str(e) != "timed out":
                        sleep(0.25)
                        continue
                    else:
                        print(out_string)
                        raise

            if not status:
                raise Exception("Did not get a response")

            if not manager_dict["no_logs"]:
                log(f"OK: {out_string}", log_list=log_list)

            found(ip, status, server_dict, manager_dict, default_icon)

        except Exception as e:
            if not manager_dict["no_logs"]:
                log(f"FAIL: {out_string}", log_list=log_list)

                if manager_dict["exception"] != str(e)[:50]:
                    manager_dict["exception"] = str(e)[:50]

        manager_dict["count"] += 1

if __name__ == "__main__":
    from PIL import Image, ImageTk

    from urllib.request import urlopen
    from multiprocessing import Process, Manager
    from base64 import b64decode, b64encode
    from io import BytesIO
    from tkinter import Tk, Button, Label, NW, NE, SE, SW, LEFT, HORIZONTAL
    from tkinter.ttk import Progressbar

    def status_change(button, manager_dict):
        manager_dict["awake"] = not manager_dict["awake"]
        button.config(text=("Pause" if manager_dict["awake"] else "Resume"))

    def logging_change(button, manager_dict):
        manager_dict["no_logs"] = not manager_dict["no_logs"]
        button.config(text=("Enable Logs" if manager_dict["no_logs"] else "Disable Logs"))

    def clear_log(console, log_list):
        console.config(text="")
        del log_list[0:]


    log("Starting...")

    open("finds.txt", "w").close()

    #block_urls = ["https://curben.gitlab.io/malware-filter/urlhaus-filter.txt", "https://curben.gitlab.io/malware-filter/phishing-filter.txt"]
    block_urls, bad_url_list = [], []

    min_ip_number = int(ip_address("1.0.0.0"))
    max_ip_number = int(ip_address("223.255.255.255"))
    ip_number_range = max_ip_number - min_ip_number

    log(f"Searching {'{:,}'.format(ip_number_range)} ips.")

    target_proceses, created_proceses, delay_between_creation = 300, [], False

    for block_url in block_urls:
        with urlopen(block_url) as stream:
            bad_url_list += [line.decode().rstrip() for line in stream if not line.startswith(b"!") or not line.startswith(b"#")]

    bad_url_list = set(bad_url_list)

    interval, extra = divmod(ip_number_range, target_proceses)
    current_interval = 0

    manager = Manager()

    manager_dict = manager.dict()
    manager_dict["total_found"] = 0
    manager_dict["count"] = 0
    manager_dict["awake"] = True
    manager_dict["exception"] = "None"
    manager_dict["no_logs"] = True

    server_dict = manager.dict()
    server_dict["ip"] = "IP: None"
    server_dict["description"] = 'DESCRIPTION: "None"'
    server_dict["ping"] = "PING: 0 ms"
    server_dict["version"] = "VERSION: None"
    server_dict["players"] = "PLAYERS: 0/0"
    server_dict["icon"] = None
    server_dict["update"] = False

    log_list = manager.list(["Starting...\n", f"Searching {'{:,}'.format(ip_number_range)} ips.\n"])

    if manager_dict["no_logs"]:
        log("No logs setting is on.", log_list=log_list)

    root = Tk()

    with open("assets/pack.png", "rb") as file:
        default_icon = b64encode(file.read()).decode()

    server_dict["icon"] = default_icon

    image = ImageTk.PhotoImage(Image.open(BytesIO(b64decode((server_dict["icon"].replace("=", "").replace("data:image/png;base64,", "") + "==").encode()))).resize((128, 128)))
    icon_label = Label(root, image=image, width=128, height=128)
    icon_label.place(anchor=NW, x=0, y=0)

    ip_label = Label(root, text=server_dict["ip"])
    ip_label.place(anchor=NW, x=130, y=0)

    description_label = Label(root, text=server_dict["description"])
    description_label.place(anchor=NW, x=130, y=22)

    ping_label = Label(root, text=server_dict["ping"])
    ping_label.place(anchor=NW, x=130, y=44)

    version_label = Label(root, text=server_dict["version"])
    version_label.place(anchor=NW, x=130, y=66)

    players_label = Label(root, text=server_dict["players"])
    players_label.place(anchor=NW, x=130, y=88)

    total_label = Label(root, text="TOTAL FOUND: " + str(manager_dict["total_found"]))
    total_label.place(anchor=NW, x=130, y=110)

    found_average_label = Label(root, text="Found IPs/Hour: Calculating")
    found_average_label.place(anchor=NE, relx=1.0, y=0)

    ips_average_label = Label(root, text="IPs/Minute: Calculating")
    ips_average_label.place(anchor=NE, relx=1.0, y=22)

    progress_bar = Progressbar(root, orient=HORIZONTAL, mode="determinate")
    progress_bar.place(anchor=NE, relx=1.0, y=132, relwidth=0.925)

    progress_label = Label(root, text="0.0%")
    progress_label.place(anchor=NW, x=0, y=132)

    counter_label = Label(root, text="Total IPs: " + str(manager_dict["count"]), font="none 36 bold")
    counter_label.place(anchor=NW, x=0, y=176)

    starting_label = Label(root, text="Starting...")
    starting_label.place(anchor=SW, x=0, rely=1)

    error_label = Label(root, text=(manager_dict["exception"] if not manager_dict["no_logs"] else "No logs setting is on."))
    error_label.place(anchor=SE, relx=1, rely=1)

    status_button = Button(root, text=("Pause" if manager_dict["awake"] else "Resume"), font="none 24 bold", command=lambda: status_change(status_button, manager_dict))
    status_button.place(anchor=NE, relx=1.0, y=66)

    console_box = Label(root, text="".join(log_list), bg="black", fg="white", anchor=NW, justify=LEFT)
    console_box.place(anchor=NW, rely=0.5, x=0, relwidth=1.0, relheight=0.45)

    enable_log_button = Button(root, text=("Enable Logs" if manager_dict["no_logs"] else "Disable Logs"), command=lambda: logging_change(enable_log_button, manager_dict))
    enable_log_button.place(anchor=NE, rely=0.5, relx=1.0)

    clear_button = Button(root, text="Clear Log", command=lambda: clear_log(console_box, log_list))
    clear_button.place(anchor=NE, rely=0.55, relx=1.0)

    root.title("Control Panel")
    root.geometry("600x500")
    root.resizable(False, False) 
    root.update()

    start = time()

    for process_number in range(target_proceses):
        range_min = current_interval + min_ip_number

        current_interval += interval
        if extra:
            current_interval += 1
            extra -= 1
        if process_number + 1 == target_proceses:
            current_interval += 1

        range_max = current_interval + min_ip_number

        process = Process(target=finder, daemon=True, args=(range_min, range_max, bad_url_list, manager_dict, server_dict, log_list, default_icon), name=f"Server Finder {process_number}")
        created_proceses.append(process)
        process.start()

        counter_label.config(text="Total IPs: " + "{:,}".format(manager_dict["count"]))
        starting_label.config(text=f"Starting... ({process_number + 1}/{target_proceses})")
        total_label.config(text="TOTAL FOUND: " + str(manager_dict["total_found"]))

        percentage = manager_dict["total_found"] / ip_number_range
        progress_bar.config(value=percentage)
        progress_label.config(text=str(round(percentage * 10) / 10) + "%")

        if not manager_dict["no_logs"]:
            error_label.config(text="Last Error: " + manager_dict["exception"])
            if len(log_list) > 14:
                del log_list[:len(log_list)-14]
            console_box.config(text="".join(log_list))

        root.update()

        if delay_between_creation: sleep(3 / target_proceses)

    starting_label.config(text=f"Started. ({target_proceses})")

    while any([type(process._popen.poll()) != type(0) for process in created_proceses]):
        counter_label.config(text="Total IPs: " + "{:,}".format(manager_dict["count"]))
        total_label.config(text="TOTAL FOUND: " + str(manager_dict["total_found"]))

        duration = (time() - start) / 60
        if duration:
            found_average_label.config(text="Found IPs/Hour: " + str(round(manager_dict["total_found"] / (duration / 60))))
            ips_average_label.config(text="IPs/Minute: " + str(round(manager_dict["count"] / duration)))

        percentage = manager_dict["total_found"] / ip_number_range
        progress_bar.config(value=percentage)
        progress_label.config(text=str(round(percentage * 10) / 10) + "%")

        if not manager_dict["no_logs"]:
            error_label.config(text="Last Error: " + manager_dict["exception"])
            if len(log_list) > 14:
                del log_list[:len(log_list)-14]
            console_box.config(text="".join(log_list))

        if server_dict["update"]:
            for _ in range(2):
                try: image = ImageTk.PhotoImage(Image.open(BytesIO(b64decode((server_dict["icon"].replace("=", "").replace("data:image/png;base64,", "") + "==").encode()))).resize((128, 128)))
                except: 
                    server_dict["icon"] = default_icon
                    continue

                break

            icon_label.config(image=image)

            ip_label.config(text=server_dict["ip"])
            description_label.config(text=server_dict["description"])
            ping_label.config(text=server_dict["ping"])
            version_label.config(text=server_dict["version"])
            players_label.config(text=server_dict["players"])

            server_dict["update"] = False

        root.update()
        sleep(0.1)