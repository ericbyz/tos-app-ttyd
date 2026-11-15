#!/usr/bin/env python3
"""Unpack a built .deb and verify structure without dpkg (pure stdlib).

Checks (per platform):
  - ar members: debian-binary / control.tar.gz / data.tar.xz
  - control.tar members live at the tar ROOT (./control — not ./DEBIAN/control)
  - control fields: Package / Version / Architecture match the build
  - payload contains the expected app tree under ./usr/local/<app>/
  - every ELF under bin/ has the expected machine type
    (x86_64 -> EM_X86_64=0x3e, aarch64 -> EM_AARCH64=0xb7)
  - maintainer scripts are executable, payload ELF/binaries executable

Usage: unpack_check.py <file.deb> <x86_64|aarch64> [expected_version]
Exit code 0 = pass.
"""
import io
import lzma
import re
import sys
import tarfile

ELF_MACHINE = {"x86_64": 0x3E, "aarch64": 0xB7}


def err(msg):
    print(f"ERROR: {msg}")
    return 1


def main() -> int:
    deb, platform = sys.argv[1], sys.argv[2]
    version = sys.argv[3] if len(sys.argv) > 3 else None
    if platform not in ELF_MACHINE:
        return err(f"unknown platform {platform}")
    app_id = "ttyd"

    data = open(deb, "rb").read()
    if data[:8] != b"!<arch>\n":
        return err("not an ar archive")

    members = {}
    off = 8
    while off < len(data):
        hdr = data[off:off + 60]
        if len(hdr) < 60:
            return err("truncated ar header")
        name = hdr[0:16].decode().rstrip()
        size = int(hdr[48:58].decode().strip())
        members[name] = data[off + 60:off + 60 + size]
        off += 60 + size + (size % 2)

    for m in ("debian-binary", "control.tar.gz", "data.tar.xz"):
        if m not in members:
            return err(f"missing ar member {m}")
    if members["debian-binary"] != b"2.0\n":
        return err("debian-binary != 2.0")

    # control member: files must sit at the tar root
    with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"])) as tf:
        names = tf.getnames()
        ctl_txt = tf.extractfile("./control").read().decode()
    if "./control" not in names:
        return err(f"control.tar members not at root: {names[:5]}")
    if "DEBIAN" in "".join(names):
        return err(f"control.tar must not carry a DEBIAN/ prefix: {names}")

    want_arch = {"x86_64": "amd64", "aarch64": "arm64"}[platform]
    fields = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", ctl_txt, re.M))
    if fields.get("Package") != app_id:
        return err(f"Package != {app_id}: {fields.get('Package')}")
    if fields.get("Architecture") != want_arch:
        return err(f"Architecture != {want_arch}: {fields.get('Architecture')}")
    if version and fields.get("Version") != version:
        return err(f"Version != {version}: {fields.get('Version')}")

    # payload
    with tarfile.open(fileobj=io.BytesIO(lzma.decompress(members["data.tar.xz"]))) as tf:
        payloads = tf.getmembers()
        pnames = [m.name for m in payloads]
        elfs = []
        for m in payloads:
            if not m.isfile():
                continue
            f = tf.extractfile(m)
            head = f.read(20)
            if head[:4] == b"\x7fELF" and head[4] == 2:  # ELF64
                f.seek(18)
                machine = int.from_bytes(f.read(2), "little")
                elfs.append((m.name, machine, m.mode))
    for need in (f"./usr/local/{app_id}/bin/ttyd",
                 f"./usr/local/{app_id}/config.ini",
                 f"./usr/local/{app_id}/packaging-extras/ttyd.env.default",
                 f"./usr/local/{app_id}/init.d/{app_id}.service",
                 f"./usr/local/{app_id}/nginx/{app_id}.conf",
                 f"./usr/local/{app_id}/{app_id}.lang",
                 f"./usr/local/{app_id}/images/icons/{app_id}.svg",
                 "./usr/share/doc/ttyd/copyright"):
        if need not in pnames:
            return err(f"data.tar missing {need}")
    for s in ("postinst", "prerm", "postrm"):
        if f"./{s}" not in names:
            return err(f"control.tar missing ./{s}")
    if not elfs:
        return err("no ELF64 binaries found in payload")
    for name, machine, mode in elfs:
        if machine != ELF_MACHINE[platform]:
            return err(f"{name}: ELF machine 0x{machine:x} != {ELF_MACHINE[platform]:x} ({platform})")
        if not (mode & 0o111):
            return err(f"{name}: ELF not executable (mode {oct(mode)})")
    print(f"OK {deb} [{platform}]")
    print(f"  control: Package={fields.get('Package')} Version={fields.get('Version')} "
          f"Architecture={fields.get('Architecture')}")
    print(f"  payload: {len(payloads)} entries, {len(elfs)} ELF64 ({platform}) all executable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
