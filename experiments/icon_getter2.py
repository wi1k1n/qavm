from __future__ import annotations

import io
import os
import plistlib
import struct
from pathlib import Path

from PIL import Image
import pefile


RT_ICON = 3
RT_GROUP_ICON = 14


def extract_icon(input_path: str | Path, output_png: str | Path) -> None:
    input_path = Path(input_path)
    output_png = Path(output_png)

    if input_path.suffix.lower() in {".exe", ".dll"}:
        extract_pe_icon_to_png(input_path, output_png)
    elif input_path.suffix.lower() == ".app":
        extract_macos_app_icon_to_png(input_path, output_png)
    elif input_path.suffix.lower() == ".icns":
        extract_icns_to_png(input_path, output_png)
    else:
        raise ValueError(f"Unsupported file type: {input_path}")


def extract_pe_icon_to_png(exe_path: Path, output_png: Path) -> None:
    """
    Extracts the largest icon from a Windows PE file: .exe or .dll.
    Works on Windows, macOS, and Linux.
    """
    pe = pefile.PE(str(exe_path))

    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        raise RuntimeError("No resources found in PE file")

    icon_groups = {}
    icons = {}

    for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if resource_type.id == RT_GROUP_ICON:
            for name_entry in resource_type.directory.entries:
                for lang_entry in name_entry.directory.entries:
                    data_rva = lang_entry.data.struct.OffsetToData
                    size = lang_entry.data.struct.Size
                    data = pe.get_memory_mapped_image()[data_rva:data_rva + size]
                    icon_groups[name_entry.id] = data

        elif resource_type.id == RT_ICON:
            for name_entry in resource_type.directory.entries:
                for lang_entry in name_entry.directory.entries:
                    data_rva = lang_entry.data.struct.OffsetToData
                    size = lang_entry.data.struct.Size
                    data = pe.get_memory_mapped_image()[data_rva:data_rva + size]
                    icons[name_entry.id] = data

    if not icon_groups:
        raise RuntimeError("No icon group found in PE file")

    # Take the first icon group. Most apps have one main icon group.
    group_data = next(iter(icon_groups.values()))
    ico_data = build_ico_from_group(group_data, icons)

    image = load_largest_image_from_ico_bytes(ico_data)
    image.save(output_png)


def build_ico_from_group(group_data: bytes, icons: dict[int, bytes]) -> bytes:
    """
    Converts RT_GROUP_ICON resource data + RT_ICON resources into a valid .ico file.
    """
    reserved, icon_type, count = struct.unpack_from("<HHH", group_data, 0)

    if reserved != 0 or icon_type != 1:
        raise RuntimeError("Invalid icon group resource")

    entries = []
    offset = 6 + count * 16
    icon_payloads = []

    for i in range(count):
        entry_offset = 6 + i * 14

        width, height, color_count, reserved_byte, planes, bit_count, size, icon_id = struct.unpack_from(
            "<BBBBHHIH",
            group_data,
            entry_offset,
        )

        icon_data = icons.get(icon_id)
        if icon_data is None:
            continue

        entries.append(
            struct.pack(
                "<BBBBHHII",
                width,
                height,
                color_count,
                reserved_byte,
                planes,
                bit_count,
                len(icon_data),
                offset,
            )
        )

        icon_payloads.append(icon_data)
        offset += len(icon_data)

    if not entries:
        raise RuntimeError("Icon group exists, but no matching icon images were found")

    header = struct.pack("<HHH", 0, 1, len(entries))
    return header + b"".join(entries) + b"".join(icon_payloads)


def load_largest_image_from_ico_bytes(ico_data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(ico_data))

    best = None
    best_area = -1

    for frame in range(getattr(img, "n_frames", 1)):
        try:
            img.seek(frame)
        except EOFError:
            break

        candidate = img.convert("RGBA")
        area = candidate.width * candidate.height

        if area > best_area:
            best = candidate.copy()
            best_area = area

    if best is None:
        raise RuntimeError("Could not decode ICO image")

    return best


def extract_macos_app_icon_to_png(app_path: Path, output_png: Path) -> None:
    """
    Extracts icon from a macOS .app bundle.
    """
    info_plist = app_path / "Contents" / "Info.plist"

    if not info_plist.exists():
        raise RuntimeError(f"Info.plist not found: {info_plist}")

    with info_plist.open("rb") as f:
        info = plistlib.load(f)

    icon_name = info.get("CFBundleIconFile")

    if not icon_name:
        raise RuntimeError("CFBundleIconFile not found in Info.plist")

    if not icon_name.endswith(".icns"):
        icon_name += ".icns"

    icns_path = app_path / "Contents" / "Resources" / icon_name

    if not icns_path.exists():
        raise RuntimeError(f"Icon file not found: {icns_path}")

    extract_icns_to_png(icns_path, output_png)


def extract_icns_to_png(icns_path: Path, output_png: Path) -> None:
    """
    Extracts the largest image from a macOS .icns file.
    """
    img = Image.open(icns_path)

    best = None
    best_area = -1

    for frame in range(getattr(img, "n_frames", 1)):
        try:
            img.seek(frame)
        except EOFError:
            break

        candidate = img.convert("RGBA")
        area = candidate.width * candidate.height

        if area > best_area:
            best = candidate.copy()
            best_area = area

    if best is None:
        raise RuntimeError("Could not decode ICNS image")

    best.save(output_png)


if __name__ == "__main__":
    extract_icon(r"C:\Windows\System32\notepad.exe", "notepad_icon.png")

    # macOS examples:
    # extract_icon("/Applications/Safari.app", "safari_icon.png")
    # extract_icon("/path/to/icon.icns", "icon.png")