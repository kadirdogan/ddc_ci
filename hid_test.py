import hid, time
dev = hid.device()
dev.open(0x1209, 0xC55D)
dev.set_nonblocking(False)
print('basliyor')
while True:
    data = dev.read(64, timeout_ms=1000)
    if data:
        print(data[0], data[1])