"""
Command-line entrypoint: parse module/midi -> project -> render audio+video.

Usage:
  ytpmv parse --format openmpt input.it --out project.json
  ytpmv render --project project.json --out out.mp4
  ytpmv run --input input.it --out out.mp4
"""

import argparse
import logging
import os
from .parser.base import get_parser_for_format
from .gui.project import Project
from .renderer.audio import AudioRenderer
from .renderer.video import VideoRenderer
from .samples.registry import SampleRegistry
from .utils.cache import FileCache

logger = logging.getLogger(__name__)

def parse_command(args):
    parser = get_parser_for_format(args.format)
    if not parser:
        raise SystemExit(f"No parser for format: {args.format}")
    events = parser.parse(args.input)
    proj = Project(events=events)
    proj.save(args.out)
    print("Project saved:", args.out)

def render_command(args):
    proj = Project.load(args.project)
    # sample registry from mapping
    reg = SampleRegistry()
    for name, path in (proj.sample_map or {}).items():
        reg.register(name, path)
    cache = FileCache(".ytpmv_cache")
    audio_renderer = AudioRenderer(reg, cache=cache)
    audio_out = args.out.replace(".mp4", ".wav")
    audio_renderer.render(proj.events, audio_out, chunk_size=args.chunk, tempo_bpm=args.tempo, workers=args.workers)
    dur = max((e.start + e.duration) for e in proj.events) if proj.events else 0.0
    video_renderer = VideoRenderer(duration=dur, size=(args.width, args.height), fps=args.fps)
    video_renderer.render(proj.events, audio_out, args.out)
    print("Rendered:", args.out)

def run_command(args):
    # parse auto-detect
    fmt = args.format
    if not fmt:
        ext = os.path.splitext(args.input)[1].lower()
        if ext in (".mid", ".midi"):
            fmt = "midi"
        else:
            fmt = "openmpt"
    parser = get_parser_for_format(fmt)
    if not parser:
        raise SystemExit(f"No parser for: {fmt}")
    events = parser.parse(args.input)
    proj = Project(events=events)
    # simple sample map discovery: same-folder WAVs named by sample names are not assumed; user should assign.
    reg = SampleRegistry()
    cache = FileCache(".ytpmv_cache")
    audio_renderer = AudioRenderer(reg, cache=cache)
    audio_out = args.out.replace(".mp4", ".wav")
    audio_renderer.render(events, audio_out, chunk_size=args.chunk, tempo_bpm=args.tempo, workers=args.workers)
    dur = max((e.start + e.duration) for e in events) if events else 0.0
    video_renderer = VideoRenderer(duration=dur, size=(args.width, args.height), fps=args.fps)
    video_renderer.render(events, audio_out, args.out)
    print("Done:", args.out)

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="ytpmv")
    sub = ap.add_subparsers(dest="cmd")
    p_parse = sub.add_parser("parse")
    p_parse.add_argument("--format", required=True, help="parser format (openmpt|midi)")
    p_parse.add_argument("input")
    p_parse.add_argument("--out", required=True)
    p_render = sub.add_parser("render")
    p_render.add_argument("--project", required=True)
    p_render.add_argument("--out", required=True)
    p_render.add_argument("--chunk", type=float, default=8.0)
    p_render.add_argument("--tempo", type=float, default=None)
    p_render.add_argument("--workers", type=int, default=2)
    p_render.add_argument("--fps", type=int, default=24)
    p_render.add_argument("--width", type=int, default=1280)
    p_render.add_argument("--height", type=int, default=720)
    p_run = sub.add_parser("run")
    p_run.add_argument("input")
    p_run.add_argument("--format", choices=["openmpt","midi"], default=None)
    p_run.add_argument("--out", required=True)
    p_run.add_argument("--chunk", type=float, default=8.0)
    p_run.add_argument("--tempo", type=float, default=None)
    p_run.add_argument("--workers", type=int, default=2)
    p_run.add_argument("--fps", type=int, default=24)
    p_run.add_argument("--width", type=int, default=1280)
    p_run.add_argument("--height", type=int, default=720)
    args = ap.parse_args()
    if args.cmd == "parse":
        parse_command(args)
    elif args.cmd == "render":
        render_command(args)
    elif args.cmd == "run":
        run_command(args)
    else:
        ap.print_help()