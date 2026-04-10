from monitorcontrol import get_monitors
for monitor in get_monitors():
    with monitor:
        caps = monitor.get_vcp_capabilities()
        print(caps)