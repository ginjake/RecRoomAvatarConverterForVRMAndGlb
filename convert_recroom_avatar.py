import argparse
import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


DEFAULT_BLENDER_CANDIDATES = [
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
]


@dataclass
class ConverterConfig:
    blender_candidates: list[Path] = field(
        default_factory=lambda: [Path(value) for value in DEFAULT_BLENDER_CANDIDATES]
    )
    vrm_addon_sources: list[Path] = field(default_factory=list)


@dataclass
class ConversionRequest:
    input_glb: Path
    output_vrm: Path
    blender_path: Path
    keep_blend: bool = True
    skip_vrm: bool = False
    vrm_addon_source: Path | None = None


def default_config_path() -> Path:
    return Path.cwd() / "recroom_converter.toml"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_data_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    if getattr(sys, "frozen", False):
        internal_dir = app_base_dir() / "_internal"
        if internal_dir.is_dir():
            return internal_dir
    return app_base_dir()


def blender_script_path() -> Path:
    candidate = bundled_data_dir() / "recroom_to_vrm_blender.py"
    if candidate.is_file():
        return candidate
    return Path(__file__).with_name("recroom_to_vrm_blender.py").resolve()


def log_file_path() -> Path:
    return app_base_dir() / "RecRoomVrmConverter.log"


def append_log_line(message: str) -> None:
    try:
        with log_file_path().open("a", encoding="utf-8") as file:
            file.write(message.rstrip() + "\n")
    except OSError:
        pass


def load_config(path: Path | None) -> ConverterConfig:
    config = ConverterConfig()
    config_path = path or default_config_path()
    if not config_path.is_file():
        return config

    with config_path.open("rb") as file:
        data = tomllib.load(file)

    blender = data.get("blender", {})
    addon = data.get("vrm_addon", {})

    if isinstance(blender.get("candidates"), list):
        config.blender_candidates = [Path(str(value)) for value in blender["candidates"]]
    if isinstance(addon.get("sources"), list):
        config.vrm_addon_sources = [Path(str(value)) for value in addon["sources"]]
    return config


def find_blender(explicit: str | None, config: ConverterConfig) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"Blender not found: {path}")
        return path
    for candidate in config.blender_candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Blender executable was not found. Pass --blender with a full path or add candidates to recroom_converter.toml."
    )


def resolve_vrm_addon_source(
    explicit: str | None, config: ConverterConfig
) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"VRM addon source not found: {path}")
        return path.resolve()
    bundled_source = (
        bundled_data_dir() / "vendor" / "VRM-Addon-for-Blender" / "src" / "io_scene_vrm"
    )
    if bundled_source.exists():
        return bundled_source.resolve()
    for source in config.vrm_addon_sources:
        if source.exists():
            return source.resolve()
    return None


def default_vrm_addon_source(config: ConverterConfig) -> Path | None:
    return resolve_vrm_addon_source(None, config)


def build_request(args: argparse.Namespace, config: ConverterConfig) -> ConversionRequest:
    input_glb = args.input_glb.resolve()
    output_vrm = args.output_vrm.resolve()
    blender_path = find_blender(args.blender, config)
    vrm_addon_source = resolve_vrm_addon_source(args.vrm_addon_source, config)

    if not input_glb.is_file():
        raise FileNotFoundError(f"Input GLB not found: {input_glb}")
    if output_vrm.suffix.lower() != ".vrm":
        raise ValueError("Output path must use a .vrm extension.")

    output_vrm.parent.mkdir(parents=True, exist_ok=True)
    return ConversionRequest(
        input_glb=input_glb,
        output_vrm=output_vrm,
        blender_path=blender_path,
        keep_blend=bool(args.keep_blend) or not bool(args.no_blend),
        skip_vrm=bool(args.skip_vrm),
        vrm_addon_source=vrm_addon_source,
    )


def build_command(request: ConversionRequest) -> list[str]:
    script_path = blender_script_path()
    command = [
        str(request.blender_path),
        "--background",
        "--python",
        str(script_path),
        "--",
        "--input",
        str(request.input_glb),
        "--output",
        str(request.output_vrm),
    ]
    if request.keep_blend:
        command.append("--keep-blend")
    if request.skip_vrm:
        command.append("--skip-vrm")
    if request.vrm_addon_source:
        command.extend(["--vrm-addon-source", str(request.vrm_addon_source)])
    return command


def run_conversion(
    request: ConversionRequest, log_callback: Callable[[str], None] | None = None
) -> int:
    append_log_line(f"Starting conversion: {request.input_glb} -> {request.output_vrm}")
    saw_error = False
    error_markers = (
        "Traceback (most recent call last):",
        "RuntimeError:",
        "VRM export failed:",
    )
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        build_command(request),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    if process.stdout:
        for line in process.stdout:
            stripped = line.rstrip()
            if any(marker in stripped for marker in error_markers):
                saw_error = True
            append_log_line(stripped)
            if log_callback:
                log_callback(stripped)
    exit_code = process.wait()
    if not request.skip_vrm and not request.output_vrm.is_file():
        saw_error = True
        message = f"Output VRM was not created: {request.output_vrm}"
        append_log_line(message)
        if log_callback:
            log_callback(message)
    if exit_code == 0 and saw_error:
        exit_code = 1
    append_log_line(f"Conversion finished with exit code {exit_code}")
    return exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Rec Room avatar GLB into a rigged GLB or VRM via Blender."
    )
    parser.add_argument("input_glb", type=Path, help="Path to the Rec Room GLB")
    parser.add_argument("output_vrm", type=Path, help="Target .vrm path")
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional TOML config file. Defaults to ./recroom_converter.toml if present.",
    )
    parser.add_argument(
        "--blender",
        help="Path to blender.exe. Defaults to configured or common install locations.",
    )
    parser.add_argument(
        "--keep-blend",
        action="store_true",
        help="Keep the intermediate .blend file next to the output. This is now the default.",
    )
    parser.add_argument(
        "--no-blend",
        action="store_true",
        help="Do not save the intermediate .blend file.",
    )
    parser.add_argument(
        "--skip-vrm",
        action="store_true",
        help="Only generate a rigged GLB, even if a VRM addon is available.",
    )
    parser.add_argument(
        "--vrm-addon-source",
        help=(
            "Optional path to a VRM addon directory or zip. "
            "If no compatible VRM addon is enabled, this source is installed first."
        ),
    )
    parser.add_argument(
        "--print-environment",
        action="store_true",
        help="Print the resolved Blender path and addon source, then exit.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        config = load_config(args.config)
        request = build_request(args, config)

        if args.print_environment:
            print(f"blender={request.blender_path}")
            print(f"vrm_addon_source={request.vrm_addon_source}")
            return 0

        return run_conversion(request, print)
    except Exception as exc:
        append_log_line(f"Fatal error: {exc}")
        raise


if __name__ == "__main__":
    sys.exit(main())
