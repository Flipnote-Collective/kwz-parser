
import struct

values = [0, 1, 0xF, 0x10, 0x11, 0x1F, 0xF0, 0xF1, 0xFF]

fields = []
for a in range(9):
    for b in range(9):
        for c in range(9):
            for d in range(9):
                value = (values[a] << 24) | (values[b] << 16) | \
                        (values[c] << 8) | values[d]
                fields.append(value)

data = struct.pack(">%iI" % len(fields), *fields)
with open("comptable2.bin", "wb") as f:
    f.write(data)
