import hid
dev = hid.device()
dev.open(0x1209, 0xC55D)
dev.set_nonblocking(False)
print('basliyor')
for i in range(20):
    data = dev.read(64, timeout_ms=500)
    print(i, data[:4] if data else 'bos')