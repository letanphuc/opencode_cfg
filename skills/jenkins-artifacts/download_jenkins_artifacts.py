#!/usr/bin/env python3
"""Download Jenkins build artifacts from the Jenkins SMB archive.

Examples:
  ./download_jenkins_artifacts.py BuildWearOS7-BB2 19
  ./download_jenkins_artifacts.py BuildWearOS7-BB2 19 --filter '**/eMMC/'
  ./download_jenkins_artifacts.py BuildWearOS7-BB2 19 --filter '*.img'
"""

import argparse
import fnmatch
import os
import posixpath
import sys
import time
import uuid

from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.open import (
    CreateDisposition,
    CreateOptions,
    DirectoryAccessMask,
    FileAttributes,
    FileInformationClass,
    ImpersonationLevel,
    Open,
    ShareAccess,
)
from smbprotocol.exceptions import SMBResponseException


DEFAULT_HOST = "192.168.1.114"
DEFAULT_SHARE = "Jenkins"
DEFAULT_USER = "mijo"
DEFAULT_OUT = "download"
READ_SIZE = 1024 * 1024


def decode(value):
    if hasattr(value, "get_value"):
        value = value.get_value()
    if isinstance(value, bytes):
        return value.decode("utf-16-le", errors="replace").rstrip("\x00")
    return str(value)


def connect(host, share, user, password):
    connection = Connection(uuid.uuid4(), host, port=445)
    connection.connect()
    session = Session(connection, username=user, password=password)
    session.connect()
    tree = TreeConnect(session, share)
    tree.connect()
    return connection, tree


def open_dir(tree, path):
    handle = Open(tree, path)
    handle.create(
        ImpersonationLevel.Impersonation,
        DirectoryAccessMask.GENERIC_READ,
        FileAttributes.FILE_ATTRIBUTE_DIRECTORY,
        ShareAccess.FILE_SHARE_READ | ShareAccess.FILE_SHARE_WRITE,
        CreateDisposition.FILE_OPEN,
        CreateOptions.FILE_DIRECTORY_FILE,
    )
    return handle


def list_dir(tree, path):
    handle = open_dir(tree, path)
    try:
        entries = handle.query_directory("*", FileInformationClass.FILE_DIRECTORY_INFORMATION)
        out = []
        for entry in entries:
            name = decode(entry["file_name"])
            if name in (".", ".."):
                continue
            attrs = entry["file_attributes"].get_value()
            out.append((name, bool(attrs & FileAttributes.FILE_ATTRIBUTE_DIRECTORY)))
        return out
    finally:
        handle.close()


def join_remote(*parts):
    return "\\".join(str(part).strip("\\/") for part in parts if str(part).strip("\\/"))


def unc_path(host, share, remote_path):
    return "\\\\" + "\\".join([host, share, remote_path])


def crawl(tree, remote_dir, prefix=""):
    for name, is_dir in list_dir(tree, remote_dir):
        rel = posixpath.join(prefix, name)
        remote_path = join_remote(remote_dir, name)
        if is_dir:
            yield from crawl(tree, remote_path, rel)
        else:
            yield rel, remote_path


def matches(rel, patterns):
    if not patterns:
        return True
    rel = rel.lstrip("/")
    basename = posixpath.basename(rel)
    for pattern in patterns:
        pattern = pattern.lstrip("/")
        if pattern.endswith("/"):
            directory = pattern.rstrip("/")
            if fnmatch.fnmatch(posixpath.dirname(rel) + "/", pattern) or fnmatch.fnmatch(rel, directory + "/*"):
                return True
            continue
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(basename, pattern):
            return True
    return False


def download_file(tree, remote_path, local_path):
    ok_file = os.path.join(os.path.dirname(local_path), "." + os.path.basename(local_path) + ".ok")
    if os.path.exists(ok_file) and os.path.exists(local_path):
        return os.path.getsize(local_path), True

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    tmp_path = local_path + ".tmp"

    handle = Open(tree, remote_path)
    handle.create(
        ImpersonationLevel.Impersonation,
        DirectoryAccessMask.GENERIC_READ,
        FileAttributes.FILE_ATTRIBUTE_NORMAL,
        ShareAccess.FILE_SHARE_READ,
        CreateDisposition.FILE_OPEN,
        CreateOptions.FILE_NON_DIRECTORY_FILE,
    )
    try:
        total = 0
        offset = 0
        with open(tmp_path, "wb") as out:
            while True:
                try:
                    data = handle.read(offset, READ_SIZE)
                except SMBResponseException as exc:
                    if "STATUS_END_OF_FILE" in str(exc):
                        break
                    raise
                if not data:
                    break
                out.write(data)
                total += len(data)
                offset += len(data)
    finally:
        handle.close()

    os.replace(tmp_path, local_path)
    with open(ok_file, "w", encoding="utf-8") as marker:
        marker.write("done\n")
    return total, False


def main():
    parser = argparse.ArgumentParser(description="Download artifacts from a Jenkins build via SMB.")
    parser.add_argument("job", help="Jenkins job name, for example BuildWearOS7-BB2")
    parser.add_argument("build", type=int, help="Jenkins build number")
    parser.add_argument("patterns", nargs="*", help="Optional glob filters")
    parser.add_argument("--filter", "-f", action="append", default=[], help="Glob filter; repeatable")
    parser.add_argument("--out", "-o", default=DEFAULT_OUT, help=f"Output directory (default: {DEFAULT_OUT})")
    parser.add_argument("--host", default=os.environ.get("JENKINS_SMB_HOST", DEFAULT_HOST), help=f"SMB host (default: {DEFAULT_HOST})")
    parser.add_argument("--share", default=os.environ.get("JENKINS_SMB_SHARE", DEFAULT_SHARE), help=f"SMB share (default: {DEFAULT_SHARE})")
    parser.add_argument("--user", default=os.environ.get("JENKINS_SMB_USER", DEFAULT_USER), help="SMB username, or JENKINS_SMB_USER")
    parser.add_argument("--password", default=os.environ.get("JENKINS_SMB_PASSWORD"), help="SMB password, or JENKINS_SMB_PASSWORD")
    parser.add_argument("--dry-run", action="store_true", help="List matching files without downloading")
    args = parser.parse_args()

    patterns = args.filter + args.patterns
    if not args.password:
        print("ERROR: Set JENKINS_SMB_PASSWORD or pass --password.", file=sys.stderr)
        return 1

    remote_root = join_remote("jobs", args.job, "builds", args.build, "archive", "Artifact", args.build)
    out_root = os.path.join(args.out, args.job, str(args.build))

    print(f"Listing: {unc_path(args.host, args.share, remote_root)}")
    matched = 0
    connection = None
    try:
        connection, tree = connect(args.host, args.share, args.user, args.password)
        for rel, remote_path in crawl(tree, remote_root):
            if not matches(rel, patterns):
                continue
            matched += 1
            local_path = os.path.join(out_root, *rel.split("/"))
            if args.dry_run:
                print(rel)
                continue
            t0 = time.time()
            size, cached = download_file(tree, remote_path, local_path)
            mb = size / 1048576
            if cached:
                print(f"  {rel}  cached ({mb:.2f} MiB)")
            else:
                print(f"  {rel}  {mb:.2f} MiB ({time.time() - t0:.1f}s)")
    except SMBResponseException as exc:
        if "STATUS_OBJECT_PATH_NOT_FOUND" in str(exc):
            print("No artifacts matched.")
            return 1
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.disconnect()

    if matched == 0:
        print("No artifacts matched.")
        return 1
    if not args.dry_run:
        print(f"\nDone. Files in: {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
