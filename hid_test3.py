import hid, time
dev = hid.device()
dev.open(0x1209, 0xC55D)
dev.set_nonblocking(True)
min_b, max_b = 255, 0
while True:
    data = dev.read(64)
    if data:
        b = data[0]
        if b < min_b: min_b = b
        if b > max_b: max_b = b
        print(f"now={b:3d}  min={min_b:3d}  max={max_b:3d}")
    time.sleep(0.05)