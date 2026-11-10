"""
Re-time a classic pcap file with integer arithmetic.

Every packet timestamp t becomes  OFFSET + (t - t0) * NUM / DEN,  where t0 is
the first timestamp in the file. Packet bytes, lengths and order are copied
unchanged. The output always uses nanosecond timestamps, so factors 16/10 and
13/10 are exact for microsecond input. NUM = DEN = 1 gives the re-based
baseline (same intervals, origin moved to OFFSET).

Usage: retime_pcap.py IN.pcap OUT.pcap NUM DEN
"""
import struct
import sys

OFFSET_NS = 1_000_000_000          # first packet at t = 1 s
MAGIC_US, MAGIC_NS = 0xA1B2C3D4, 0xA1B23C4D


def retime(src, dst, num, den):
    with open(src, "rb") as f:
        head = f.read(24)
        if len(head) < 24:
            raise ValueError("not a pcap file")
        for endian in ("<", ">"):
            magic = struct.unpack(endian + "I", head[:4])[0]
            if magic in (MAGIC_US, MAGIC_NS):
                break
        else:
            raise ValueError("unknown pcap magic (pcapng is not supported; split with tcpdump first)")
        frac_to_ns = 1000 if magic == MAGIC_US else 1
        rest = head[4:]
        n, t0, inexact = 0, None, 0
        with open(dst, "wb") as g:
            g.write(struct.pack(endian + "I", MAGIC_NS) + rest)
            while True:
                rh = f.read(16)
                if len(rh) < 16:
                    break
                sec, frac, incl, orig = struct.unpack(endian + "IIII", rh)
                data = f.read(incl)
                if len(data) < incl:
                    break                      # truncated last record, as tcpdump would drop it
                t = sec * 1_000_000_000 + frac * frac_to_ns
                if t0 is None:
                    t0 = t
                scaled = (t - t0) * num
                if scaled % den:
                    inexact += 1
                t2 = OFFSET_NS + scaled // den
                g.write(struct.pack(endian + "IIII", t2 // 1_000_000_000, t2 % 1_000_000_000, incl, orig))
                g.write(data)
                n += 1
    return n, inexact


if __name__ == "__main__":
    src, dst, num, den = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    n, inexact = retime(src, dst, num, den)
    print(f"{n} packets, {inexact} inexact divisions, factor {num}/{den} -> {dst}")
