#!/usr/bin/env python3
"""Collect an explicit allowlist of read-only Switch diagnostic evidence."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import zipfile

LOG_NAMES = ('switch-diagnostics.log', 'vulkan-test.log', 'vulkan-present.log',
             'minecraft-launcher.log', 'java-test.log', 'ffi-test.log',
             'snapshot-vulkan.json', 'zero-services-test.log', 'java25-test.log',
             'java25-vm-stdout.log', 'java25-vm-stderr.log', 'switchcraft-java25.log',
             'switchcraft-java25-vm-stdout.log', 'switchcraft-java25-vm-stderr.log',
             'launcher-task-report.json', 'vulkan-present-result.json')
ATTEMPT_LOG = re.compile(r'(?:java25-vm|switchcraft-java25-vm)-[0-9]+-(?:stdout|stderr)\.log\Z')
ATTEMPT_PRESENT = re.compile(r'vulkan-present-result-[0-9]+\.json\Z')
LIMIT = 8 * 1024 * 1024


def read_safe(root, relative):
    path = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('refusing symlink: ' + relative.as_posix())
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError('not a regular file or exceeds 8 MiB: ' + relative.as_posix())
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('file exceeds 8 MiB: ' + relative.as_posix())
    return data


def collect(sd_root, output):
    root = Path(sd_root).resolve(strict=True)
    out = Path(output).resolve()
    if not root.is_dir() or out == root or root in out.parents:
        raise ValueError('output must be outside the SD root')
    paths = [Path('manifest.json')] + [Path('switch/mc-runtime/logs') / n for n in LOG_NAMES]
    logs = root / 'switch/mc-runtime/logs'
    if logs.is_symlink():
        raise ValueError('refusing symlink: switch/mc-runtime/logs')
    attempts = sorted(p.name for p in logs.iterdir()
                      if ATTEMPT_LOG.fullmatch(p.name) or ATTEMPT_PRESENT.fullmatch(p.name)) if logs.is_dir() else []
    if len(attempts) > 128:
        raise ValueError('more than 128 attempt captures; export them in separate reviewed batches')
    paths += [Path('switch/mc-runtime/logs') / n for n in attempts]
    contents, missing = [], []
    for relative in paths:
        data = read_safe(root, relative)
        if data is None:
            missing.append(relative.as_posix())
        else:
            contents.append((relative.as_posix(), data))
    if not contents:
        raise ValueError('no allowed diagnostic files found')
    summary = {'hardware_status': 'NOT VERIFIED by collection', 'missing': missing,
               'files': [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                         for name, data in contents],
               'crash_reports': 'not collected; review and attach manually if needed'}
    with open(out, 'xb') as file:
        with zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in contents:
                archive.writestr(name, data)
            archive.writestr('collection.json', json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sd-root', required=True, help='mounted SD root or a copied SD-root directory')
    parser.add_argument('--output', required=True, help='new ZIP path outside the SD root')
    args = parser.parse_args()
    try:
        result = collect(args.sd_root, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, 'Collection failed: ' + str(exc) + '\n')
    print('Collected', len(result['files']), 'files;', len(result['missing']), 'not found.')
    print('Review contents before sharing. Crash reports are excluded; review them separately.')


if __name__ == '__main__':
    main()
