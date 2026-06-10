#!/usr/bin/env -S /Users/phuc/.config/opencode/skills/gerrit/venv/bin/python
import argparse
from dataclasses import dataclass
from email.utils import formatdate
import fnmatch
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Sequence

from loguru import logger


@dataclass(frozen=True)
class GerritConnection:
    user: str
    host: str
    port: int = 29418


class GerritClient:
    def __init__(self, connection: GerritConnection):
        self.connection = connection

    def run_query(self, query_parts: Sequence[str]) -> List[Dict[str, Any]]:
        cmd = [
            "ssh",
            "-p",
            str(self.connection.port),
            f"{self.connection.user}@{self.connection.host}",
            "gerrit",
            "query",
            "--format=JSON",
            *query_parts,
        ]
        logger.info(f"Running {cmd}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        items = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("type") == "stats":
                continue
            items.append(item)

        return items

    def get_all_changes_by_topic(
        self, topic: str, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        all_changes: List[Dict[str, Any]] = []
        skip = 0

        while True:
            changes = self.run_query(
                [
                    "--current-patch-set",
                    f"topic:{topic}",
                    f"limit:{page_size}",
                    f"--start={skip}",
                ]
            )

            if not changes:
                break

            all_changes.extend(changes)

            if len(changes) < page_size:
                break

            skip += page_size

        return all_changes

    def list_projects(self, prefix: str) -> List[str]:
        cmd = [
            "ssh",
            "-p",
            str(self.connection.port),
            f"{self.connection.user}@{self.connection.host}",
            "gerrit",
            "ls-projects",
            "--prefix",
            prefix,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def expand_project_glob(self, pattern: str) -> List[str]:
        if "*" not in pattern and "?" not in pattern and "[" not in pattern:
            return [pattern]

        prefix = pattern.split("*")[0]
        if not prefix:
            raise ValueError(f"Cannot resolve wildcard at start of project pattern: {pattern}")

        all_projects = self.list_projects(prefix)
        matched = [p for p in all_projects if fnmatch.fnmatch(p, pattern)]

        if not matched:
            logger.warning("No projects match pattern: {}", pattern)
        else:
            logger.info("Expanded '{}' -> {} project(s): {}", pattern, len(matched), matched)

        return matched

    def get_change_by_number(self, number: str) -> Optional[Dict[str, Any]]:
        changes = self.run_query(
            [
                "--current-patch-set",
                f"change:{number}",
                "limit:1",
            ]
        )
        if not changes:
            return None
        return changes[0]

    def get_change_by_number_with_files(self, number: str) -> Optional[Dict[str, Any]]:
        changes = self.run_query(
            [
                "--current-patch-set",
                "--files",
                "--commit-message",
                f"change:{number}",
                "limit:1",
            ]
        )
        if not changes:
            return None
        return changes[0]

    def git_archive(
        self, project: str, treeish: str, files: List[str], output_dir: str
    ) -> None:
        ssh_url = f"ssh://{self.connection.user}@{self.connection.host}:{self.connection.port}/{project}"
        cmd = [
            "git", "archive", f"--remote={ssh_url}", treeish,
            *files,
        ]
        logger.info("Running git archive -> {}", output_dir)
        result = subprocess.run(cmd, capture_output=True, check=True)
        os.makedirs(output_dir, exist_ok=True)
        subprocess.run(["tar", "xf", "-", "-C", output_dir],
                       input=result.stdout, capture_output=True, check=True)

    def post_review(
        self,
        change_id: str,
        message: Optional[str] = None,
        code_review: Optional[str] = None,
        verified: Optional[str] = None,
    ) -> None:
        """Post a review comment and/or vote on a Gerrit change via SSH."""
        cmd = [
            "ssh",
            "-p",
            str(self.connection.port),
            f"{self.connection.user}@{self.connection.host}",
            "gerrit",
            "review",
            change_id,
        ]
        if message:
            cmd.extend(["--message", shlex.quote(message)])
        if code_review:
            cmd.extend(["--code-review", code_review])
        if verified:
            cmd.extend(["--verified", verified])

        logger.info("Posting review on {}: code-review={}, verified={}, msg_len={}",
                     change_id, code_review, verified, len(message or ""))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("Review failed (rc={}): {}", result.returncode, result.stderr.strip())
            return
        if result.stdout.strip():
            logger.info("Response: {}", result.stdout.strip())
        if result.stderr.strip():
            logger.info("{}", result.stderr.strip())

    def _build_query_str(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        reviewer: Optional[str] = None,
        label: Optional[str] = None,
        branch: Optional[str] = None,
        project: Optional[List[str]] = None,
        status: Optional[str] = None,
        topic: Optional[str] = None,
        message: Optional[str] = None,
        comment: Optional[str] = None,
        path: Optional[str] = None,
        age: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        is_: Optional[str] = None,
        has: Optional[str] = None,
    ) -> str:
        if query:
            return query

        query_terms: List[str] = []

        if author:
            query_terms.append(f"owner:{author}")
        if reviewer:
            query_terms.append(f"reviewer:{reviewer}")
        if label:
            query_terms.append(f"label:{label}")
        if branch:
            query_terms.append(f"branch:{branch}")
        if project:
            expanded: List[str] = []
            for p in project:
                expanded.extend(self.expand_project_glob(p))
            if expanded:
                if len(expanded) == 1:
                    query_terms.append(f"project:{expanded[0]}")
                else:
                    query_terms.append(
                        "(" + " OR ".join(f"project:{p}" for p in expanded) + ")"
                    )
        if status:
            query_terms.append(f"status:{status}")
        if topic:
            query_terms.append(f"topic:{topic}")
        if message:
            query_terms.append(f"message:{message}")
        if comment:
            query_terms.append(f"comment:{comment}")
        if path:
            query_terms.append(f"path:{path}")
        if age:
            query_terms.append(f"age:{age}")
        if after:
            query_terms.append(f"after:{after}")
        if before:
            query_terms.append(f"before:{before}")
        if is_:
            query_terms.append(f"is:{is_}")
        if has:
            query_terms.append(f"has:{has}")

        if not query_terms:
            query_terms.append("status:open")

        return " ".join(query_terms)

    def search_changes(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        reviewer: Optional[str] = None,
        label: Optional[str] = None,
        branch: Optional[str] = None,
        project: Optional[List[str]] = None,
        status: Optional[str] = None,
        topic: Optional[str] = None,
        message: Optional[str] = None,
        comment: Optional[str] = None,
        path: Optional[str] = None,
        age: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        is_: Optional[str] = None,
        has: Optional[str] = None,
        limit: int = 50,
        fetch_all: bool = False,
    ) -> List[Dict[str, Any]]:
        query_str = self._build_query_str(
            query=query,
            author=author,
            reviewer=reviewer,
            label=label,
            branch=branch,
            project=project,
            status=status,
            topic=topic,
            message=message,
            comment=comment,
            path=path,
            age=age,
            after=after,
            before=before,
            is_=is_,
            has=has,
        )

        if not fetch_all:
            return self.run_query(
                [
                    "--current-patch-set",
                    query_str,
                    f"limit:{limit}",
                ]
            )

        all_changes: List[Dict[str, Any]] = []
        page_size = 100
        skip = 0

        while True:
            changes = self.run_query(
                [
                    "--current-patch-set",
                    query_str,
                    f"limit:{page_size}",
                    f"--start={skip}",
                ]
            )

            if not changes:
                break

            all_changes.extend(changes)

            if len(changes) < page_size:
                break

            skip += page_size

        return all_changes


def format_change_summary(change: Dict[str, Any]) -> str:
    number = change.get("number", "?")
    subject = change.get("subject", "")
    project = change.get("project", "")
    branch = change.get("branch", "")
    owner = change.get("owner", {}).get(
        "name", change.get("owner", {}).get("username", "?")
    )
    status = change.get("status", "?")
    labels = change.get("labels", {})

    label_parts = []
    for name, info in labels.items():
        if isinstance(info, dict):
            approved = info.get("approved", {})
            if approved:
                label_parts.append(f"{name}{approved.get('value', '')}")
            rejected = info.get("rejected", {})
            if rejected:
                label_parts.append(f"{name}{rejected.get('value', '')}")
    label_str = " ".join(label_parts) if label_parts else "-"

    return (
        f"#{number:<7} {status:<10} {project:<30} {branch:<20} "
        f"{owner:<15} {label_str:<20} {subject}"
    )


class ManifestRepoMap:
    """Maps Gerrit project names to local paths using west or repo manifest."""

    def __init__(self, repo_to_path: Dict[str, str]):
        self.repo_to_path = repo_to_path

    @classmethod
    def auto(cls) -> "ManifestRepoMap":
        """Detect workspace type and build the map."""
        cwd = Path.cwd()

        # Check for AOSP repo (find .repo/ upwards)
        search = cwd
        while search != search.parent:
            if (search / ".repo").is_dir():
                try:
                    return cls.from_repo_list()
                except Exception:
                    pass
                break
            search = search.parent

        # Fall back to west
        return cls.from_west_list()

    @classmethod
    def from_repo_list(cls) -> "ManifestRepoMap":
        """Parse `repo list` output: <local_path> : <gerrit_project>"""
        repo_to_path: Dict[str, str] = {}

        result = subprocess.run(
            ["repo", "list", "-q"],
            capture_output=True, text=True,
        )
        # repo prints a new-version banner to stderr, skip it
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if " : " not in line:
                continue
            local_path, project = line.split(" : ", 1)
            repo_to_path[project.strip()] = local_path.strip()

        if not repo_to_path:
            raise RuntimeError("repo list returned empty — not a repo workspace?")

        return cls(repo_to_path=repo_to_path)

    @classmethod
    def from_west_list(cls) -> "ManifestRepoMap":
        repo_to_path: Dict[str, str] = {}

        result = subprocess.run(
            ["west", "list", "--format={url} {path}"],
            capture_output=True, text=True, check=True,
        )

        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            url, local_path = parts

            # Extract Gerrit project name from ssh URL
            # e.g. ssh://gerrit-ssh.mijo.services:29418/mijo/ui-framework/applications/watchface-format
            #   -> mijo/ui-framework/applications/watchface-format
            if url.startswith("ssh://"):
                path_part = url.split("://", 1)[1]  # "host:port/path"
                after_port = path_part.split(":", 1)[1] if ":" in path_part else ""
                # after_port is like "29418/mijo/ui-framework/..."
                project = after_port.split("/", 1)[1] if "/" in after_port else ""
                if project:
                    repo_to_path[project] = local_path

        return cls(repo_to_path=repo_to_path)

    def resolve_local_repo_path(self, project_name: str) -> Optional[str]:
        return self.repo_to_path.get(project_name)


class CommandRunner:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def run_git(self, repo_path: str, git_cmd: Sequence[str]) -> None:
        cmd_text = " ".join(git_cmd)
        if self.dry_run:
            logger.info("[dry-run] (cd {} && {})", repo_path, cmd_text)
            return

        logger.info("(cd {} && {})", repo_path, cmd_text)
        subprocess.run(list(git_cmd), cwd=repo_path, check=True)

    def run_shell(self, cmd: str, cwd: Optional[str] = None) -> None:
        if self.dry_run:
            if cwd:
                logger.info("[dry-run] (cd {} && {})", cwd, cmd)
            else:
                logger.info("[dry-run] {}", cmd)
            return

        if cwd:
            logger.info("(cd {} && {})", cwd, cmd)
        else:
            logger.info("{}", cmd)
        subprocess.run(cmd, cwd=cwd, shell=True, check=True)


class ChangeApplier:
    def __init__(
        self,
        connection: GerritConnection,
        repo_map: ManifestRepoMap,
        runner: CommandRunner,
        mode: str,
    ):
        self.connection = connection
        self.repo_map = repo_map
        self.runner = runner
        self.mode = mode

    def apply_change(self, change: Dict[str, Any]) -> None:
        number = str(change.get("number", ""))
        title = change.get("subject", "")
        project = change.get("project", "")
        ref = change.get("currentPatchSet", {}).get("ref", "")

        if not project or not ref:
            logger.warning("Skip change {}: missing project/ref", number)
            return

        local_path = self.repo_map.resolve_local_repo_path(project)
        if not local_path:
            logger.warning(
                "Skip change {}: cannot map project '{}' to local path", number, project
            )
            return

        logger.info("Applying change {}: {}", number, title)
        logger.info("Repo: {}", local_path)

        ssh_url = f"ssh://{self.connection.user}@{self.connection.host}:{self.connection.port}/{project}"

        if self.mode == "branch":
            self.runner.run_git(local_path, ["git", "fetch", ssh_url, ref])
            self.runner.run_git(local_path, ["git", "checkout", "-b", f"change-{number}", "FETCH_HEAD"])
        elif self.mode == "checkout":
            self.runner.run_git(local_path, ["git", "fetch", ssh_url, ref])
            self.runner.run_git(local_path, ["git", "checkout", "FETCH_HEAD"])
        elif self.mode == "cherry-pick":
            self.runner.run_git(local_path, ["git", "fetch", ssh_url, ref])
            self.runner.run_git(local_path, ["git", "cherry-pick", "FETCH_HEAD"])
        elif self.mode == "format-patch":
            self.runner.run_git(local_path, ["git", "fetch", ssh_url, ref])
            self.runner.run_git(local_path, ["git", "format-patch", "-1", "--stdout", "FETCH_HEAD"])
        elif self.mode == "pull":
            self.runner.run_git(local_path, ["git", "pull", ssh_url, ref])
        elif self.mode == "reset-to":
            self.runner.run_git(local_path, ["git", "fetch", ssh_url, ref])
            self.runner.run_git(local_path, ["git", "reset", "--hard", "FETCH_HEAD"])


def resolve_connection_args(args) -> GerritConnection:
    user = args.user or os.getenv("GERRIT_USER")
    host = args.host or os.getenv("GERRIT_HOST")

    if not user:
        raise ValueError("Missing Gerrit user. Use --user or set GERRIT_USER.")
    if not host:
        raise ValueError("Missing Gerrit host. Use --host or set GERRIT_HOST.")

    return GerritConnection(user=user, host=host, port=args.port)


def print_download_options(
    connection: GerritConnection, change_number: str, project: str, ref: str
):
    ssh_url = f"ssh://{connection.user}@{connection.host}:{connection.port}/{project}"
    fetch_cmd = f"git fetch {ssh_url} {ref}"

    logger.info("Branch:")
    logger.info("{} && git checkout -b change-{} FETCH_HEAD", fetch_cmd, change_number)
    logger.info("Checkout:")
    logger.info("{} && git checkout FETCH_HEAD", fetch_cmd)
    logger.info("Cherry Pick:")
    logger.info("{} && git cherry-pick FETCH_HEAD", fetch_cmd)
    logger.info("Format Patch:")
    logger.info("{} && git format-patch -1 --stdout FETCH_HEAD", fetch_cmd)
    logger.info("Pull:")
    logger.info("git pull {} {}", ssh_url, ref)
    logger.info("Reset To:")
    logger.info("{} && git reset --hard FETCH_HEAD", fetch_cmd)


def add_connection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--user", help="SSH user, e.g. gale (or env GERRIT_USER)")
    parser.add_argument(
        "--host", help="SSH host, e.g. gerrit-ssh.mijo.services (or env GERRIT_HOST)"
    )
    parser.add_argument("--port", type=int, default=29418, help="SSH port")


def add_search_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--query", help="Raw Gerrit query string (overrides all other filters)"
    )
    parser.add_argument("--author", help="Filter by change owner (email or username)")
    parser.add_argument("--reviewer", help="Filter by reviewer (email or username)")
    parser.add_argument(
        "--label", help="Filter by label vote, e.g. 'Code-Review=2' or 'Verified=1'"
    )
    parser.add_argument("--branch", help="Filter by target branch, e.g. 'main'")
    parser.add_argument(
        "--project",
        action="append",
        help="Filter by Gerrit project name or glob pattern (repeatable). Supports * wildcard.",
    )
    parser.add_argument("--status", help="Filter by status: open, merged, abandoned")
    parser.add_argument("--topic", help="Filter by topic name")
    parser.add_argument("--message", help="Filter by commit message text")
    parser.add_argument("--comment", help="Filter by review comment text")
    parser.add_argument("--path", help="Filter by file path in the change")
    parser.add_argument("--age", help="Filter by age, e.g. '7d', '2w', '1mon', '1y'")
    parser.add_argument("--after", help="Filter changes after date, e.g. '2024-01-01'")
    parser.add_argument("--before", help="Filter changes before date")
    parser.add_argument(
        "--is",
        dest="is_",
        help="Filter by is: operator, e.g. 'watched', 'starred', 'reviewed', 'owner'",
    )
    parser.add_argument(
        "--has",
        help="Filter by has: operator, e.g. 'draft', 'unresolved', 'edit', 'star'",
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Max results (default: 50)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all results (paginates automatically, overrides --limit)",
    )


def _derive_http_host(ssh_host: str) -> str:
    return ssh_host.replace("-ssh.", ".") if "-ssh." in ssh_host else ssh_host


def cmd_diff(args):
    connection = resolve_connection_args(args)
    client = GerritClient(connection)
    change = client.get_change_by_number(number=str(args.change))

    if not change:
        logger.error("Change not found: {}", args.change)
        return

    project = change.get("project", "")
    patch_set = change.get("currentPatchSet", {})
    ref = patch_set.get("ref", "")
    revision = patch_set.get("number", "current")
    number = change.get("number", args.change)
    subject = change.get("subject", "")

    if not project or not ref:
        logger.error("Missing project/ref in change data")
        return

    http_host = args.web_host or os.getenv("GERRIT_HTTP_HOST") or _derive_http_host(connection.host)
    encoded_project = project.replace("/", "%2F")
    url = (
        f"https://{http_host}/changes/"
        f"{encoded_project}~{number}/revisions/{revision}/patch"
        f"?download"
    )

    if args.url:
        logger.info(url)
        return

    curl_cmd = ["curl", "-fsSL"]
    http_user = args.http_user or os.getenv("GERRIT_HTTP_USER")
    http_password = args.http_password or os.getenv("GERRIT_HTTP_PASSWORD")
    if http_user and http_password:
        curl_cmd += ["-u", f"{http_user}:{http_password}"]
        url = url.replace("https://", "https://")  # unchanged, auth added
    if args.output:
        curl_cmd += ["-o", args.output]
    curl_cmd.append(url)

    logger.info("Downloading patch for change {} ({})", number, subject)
    result = subprocess.run(curl_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(
            "Download failed: {}\nURL: {}\nHint: set GERRIT_HTTP_USER and GERRIT_HTTP_PASSWORD for auth, or use --url to get the link",
            result.stderr.strip(),
            url,
        )
        return

    if args.output:
        logger.info("Saved to {}", args.output)
    else:
        print(result.stdout)


def _sanitize_filename(text: str) -> str:
    """Replace characters unsafe for filenames."""
    out = []
    for ch in text:
        if ch.isalnum() or ch in "-_.":
            out.append(ch)
        elif ch in " /\\":
            out.append("-")
    return "".join(out).strip("-")


def _diff_dirs(old_dir: str, new_dir: str, outfile: str,
               commit_msg: str, author_name: str, author_email: str,
               date_ts: int) -> None:
    old_rel = "old"
    new_rel = "new"
    parent = os.path.dirname(old_dir)
    diff_cmd = ["diff", "-ruN", old_rel, new_rel]
    result = subprocess.run(diff_cmd, cwd=parent, capture_output=True, text=True)
    diff_content = result.stdout or ""
    if result.returncode > 1:
        logger.error("diff failed: {}", result.stderr)
        raise subprocess.CalledProcessError(result.returncode, diff_cmd,
                                            result.stdout, result.stderr)

    diff_content = diff_content.replace("old/", "a/").replace("new/", "b/")

    date_str = formatdate(date_ts, localtime=False)
    subject = commit_msg.split('\n')[0]

    lines: List[str] = []
    lines.append("From: {} <{}>".format(author_name, author_email))
    lines.append("Date: {}".format(date_str))
    lines.append("Subject: {}".format(subject))
    lines.append("")
    lines.append("---")
    if diff_content.strip():
        lines.append(diff_content)
    else:
        lines.append(" (no changes)")

    with open(outfile, "w") as f:
        f.write("\n".join(lines) + "\n")


def cmd_patch(args):
    connection = resolve_connection_args(args)
    client = GerritClient(connection)

    if args.topic:
        changes_basic = client.get_all_changes_by_topic(topic=args.target)
        changes = []
        for c in changes_basic:
            num = str(c.get("number", ""))
            if num:
                detailed = client.get_change_by_number_with_files(number=num)
                if detailed:
                    changes.append(detailed)
    else:
        change = client.get_change_by_number_with_files(number=str(args.target))
        changes = [change] if change else []

    for change in changes:
        if not change:
            logger.error("Change not found: {}", args.target if not args.topic else "?")
            continue

        number = str(change.get("number", args.target))
        project = change.get("project", "")
        patch_set = change.get("currentPatchSet", {})
        revision = patch_set.get("revision", "")
        parents = patch_set.get("parents", [])
        parent_rev = parents[0] if parents else ""
        author = patch_set.get("author", {})
        author_name = author.get("name", change.get("owner", {}).get("name", ""))
        author_email = author.get("email", change.get("owner", {}).get("email", ""))
        created_on = patch_set.get("createdOn", change.get("createdOn", 0))
        commit_msg = change.get("commitMessage", change.get("subject", ""))
        files = patch_set.get("files", [])
        subject = _sanitize_filename(change.get("subject", number))
        branch = _sanitize_filename(change.get("branch", ""))

        if not project or not revision or not parent_rev:
            logger.error("Missing project/revision/parent for change {}", number)
            continue

        if not files:
            logger.warning("No files in change {}", number)
            continue

        if args.dir:
            os.makedirs(args.dir, exist_ok=True)
            outfile = os.path.join(args.dir, f"{number}-{branch}-{subject}.patch")
        elif args.output:
            outfile = args.output
        else:
            outfile = f"{number}-{branch}-{subject}.patch"

        modified_files = [f["file"] for f in files if f["type"] == "MODIFIED"]
        added_files = [f["file"] for f in files if f["type"] == "ADDED"]
        deleted_files = [f["file"] for f in files if f["type"] == "DELETED"]

        logger.info("Generating patch {} via SSH archive -> {}", number, outfile)

        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.path.join(tmpdir, "old")
            new_dir = os.path.join(tmpdir, "new")

            old_paths = modified_files + deleted_files
            new_paths = modified_files + added_files

            if old_paths:
                client.git_archive(project, parent_rev, old_paths, old_dir)
            else:
                os.makedirs(old_dir)

            if new_paths:
                client.git_archive(project, revision, new_paths, new_dir)
            else:
                os.makedirs(new_dir)

            _diff_dirs(old_dir, new_dir, outfile, commit_msg,
                       author_name, author_email, created_on)

        logger.info("Saved {}", outfile)


def cmd_get(args):
    connection = resolve_connection_args(args)
    client = GerritClient(connection)
    if str(args.target).isdigit():
        change = client.get_change_by_number(number=str(args.target))

        if not change:
            logger.error("Change not found: {}", args.target)
            return

        title = change.get("subject", "")
        project = change.get("project", "")
        ref = change.get("currentPatchSet", {}).get("ref", "")

        logger.info("Title: {}", title)
        if project and ref:
            print_download_options(connection, str(args.target), project, ref)
        else:
            logger.warning(
                "Download commands: unavailable (missing project/ref in Gerrit response)"
            )
        return

    changes = client.get_all_changes_by_topic(topic=args.target)

    logger.info("Total changes for topic '{}': {}", args.target, len(changes))
    for change in changes:
        logger.info(
            "Change ID: {}, Subject: {}", change.get("number"), change.get("subject")
        )


def cmd_search(args):
    connection = resolve_connection_args(args)
    client = GerritClient(connection)

    changes = client.search_changes(
        query=args.query,
        author=args.author,
        reviewer=args.reviewer,
        label=args.label,
        branch=args.branch,
        project=args.project or None,
        status=args.status,
        topic=args.topic,
        message=args.message,
        comment=args.comment,
        path=args.path,
        age=args.age,
        after=args.after,
        before=args.before,
        is_=args.is_,
        has=args.has,
        limit=args.limit,
        fetch_all=args.all,
    )

    if not changes:
        logger.info("No changes found matching the search criteria.")
        return

    logger.info("Found {} change(s):", len(changes))
    logger.info(
        "{:<8} {:<10} {:<30} {:<20} {:<15} {:<20} {}",
        "Number",
        "Status",
        "Project",
        "Branch",
        "Owner",
        "Labels",
        "Subject",
    )
    logger.info("-" * 140)

    for change in changes:
        logger.info(format_change_summary(change))


def cmd_review(args):
    connection = resolve_connection_args(args)
    client = GerritClient(connection)

    # Resolve change ID — if numeric, auto-append current patchset
    change_id = str(args.change)
    if change_id.isdigit():
        change = client.get_change_by_number(number=change_id)
        if not change:
            logger.error("Change not found: {}", args.change)
            return
        ps = change.get("currentPatchSet", {})
        ps_num = ps.get("number", ps.get("revision", ""))
        if ps_num:
            change_id = f"{change_id},{ps_num}"
        else:
            logger.warning("Could not resolve patchset for {}", args.change)
    elif "," in change_id:
        pass  # already has patchset
    else:
        pass  # treat as-is (e.g. commit SHA)

    client.post_review(
        change_id=change_id,
        message=args.message,
        code_review=args.code_review,
        verified=args.verified,
    )


def cmd_reset_to(args):
    connection = resolve_connection_args(args)
    client = GerritClient(connection)
    repo_map = ManifestRepoMap.auto()
    runner = CommandRunner(dry_run=args.dry_run)
    applier = ChangeApplier(
        connection=connection,
        repo_map=repo_map,
        runner=runner,
        mode=args.mode,
    )

    if str(args.target).isdigit():
        change = client.get_change_by_number(number=str(args.target))
        if not change:
            logger.error("Change not found: {}", args.target)
            return

        applier.apply_change(change)
        return

    changes = client.get_all_changes_by_topic(topic=args.target)
    if not changes:
        logger.warning("No changes found for topic: {}", args.target)
        return

    logger.info("Applying topic '{}' with {} changes", args.target, len(changes))
    for change in changes:
        applier.apply_change(change)


def cmd_reset_all(args):
    workspace_root = str(Path(__file__).resolve().parent.parent)
    manifest_path = os.path.join(workspace_root, "mijo", "manifest")
    runner = CommandRunner(dry_run=args.dry_run)

    runner.run_shell(
        "west forall -c 'git reset --hard'",
        cwd=workspace_root,
    )
    runner.run_shell("git pull", cwd=manifest_path)
    runner.run_shell("west update", cwd=workspace_root)


def build_parser():
    parser = argparse.ArgumentParser(description="Gerrit helper tool")
    subparsers = parser.add_subparsers(dest="command")

    get_parser = subparsers.add_parser(
        "get", help="Get Gerrit change by number or list all changes by topic"
    )
    get_parser.add_argument("target", help="Change number or topic name")
    add_connection_args(get_parser)
    get_parser.set_defaults(func=cmd_get)

    diff_parser = subparsers.add_parser(
        "diff", help="Download diff/patch of a Gerrit change via REST API"
    )
    diff_parser.add_argument("change", help="Change number")
    diff_parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
    )
    diff_parser.add_argument(
        "--url",
        action="store_true",
        help="Print the download URL only, do not download",
    )
    diff_parser.add_argument(
        "--web-host",
        help="Gerrit HTTP host (derived from SSH host by default, or env GERRIT_HTTP_HOST)",
    )
    diff_parser.add_argument(
        "--http-user",
        help="HTTP auth username (or env GERRIT_HTTP_USER)",
    )
    diff_parser.add_argument(
        "--http-password",
        help="HTTP auth password (or env GERRIT_HTTP_PASSWORD)",
    )
    add_connection_args(diff_parser)
    diff_parser.set_defaults(func=cmd_diff)

    patch_parser = subparsers.add_parser(
        "patch",
        help="Download Gerrit patch file via command-line (no git repo needed). "
             "Queries change metadata via SSH then fetches the patch via REST API.",
    )
    patch_parser.add_argument(
        "target",
        help="Change number (or topic name with --topic)",
    )
    patch_parser.add_argument(
        "-t", "--topic",
        action="store_true",
        help="Treat target as a topic name, download all patches in the topic",
    )
    patch_parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: auto-generated from change metadata)",
    )
    patch_parser.add_argument(
        "-d",
        "--dir",
        help="Directory to save patches into (filename is auto-generated)",
    )
    add_connection_args(patch_parser)
    patch_parser.set_defaults(func=cmd_patch)

    review_parser = subparsers.add_parser(
        "review",
        help="Post a review comment and/or vote on a Gerrit change",
    )
    review_parser.add_argument(
        "change",
        help="Change number (auto-resolves patchset), or change,patchset",
    )
    review_parser.add_argument(
        "-m", "--message",
        help="Review message/comment to post",
    )
    review_parser.add_argument(
        "--code-review",
        choices=["-2", "-1", "+1", "+2"],
        help="Code-Review vote: +2/+1/-1/-2",
    )
    review_parser.add_argument(
        "--verified",
        choices=["-1", "+1"],
        help="Verified vote: +1/-1",
    )
    add_connection_args(review_parser)
    review_parser.set_defaults(func=cmd_review)

    search_parser = subparsers.add_parser(
        "search", help="Search Gerrit changes by author, reviewer, label, branch, etc."
    )
    add_connection_args(search_parser)
    add_search_args(search_parser)
    search_parser.set_defaults(func=cmd_search)

    reset_to_parser = subparsers.add_parser(
        "reset-to",
        help="Apply a change number or topic to local repos using checkout/pull",
    )
    reset_to_parser.add_argument("target", help="Change number or topic name")
    reset_to_parser.add_argument(
        "--mode",
        choices=["branch", "checkout", "cherry-pick", "format-patch", "pull", "reset-to"],
        default="checkout",
        help="Apply mode",
    )
    reset_to_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands only; do not execute git commands",
    )
    add_connection_args(reset_to_parser)
    reset_to_parser.set_defaults(func=cmd_reset_to)

    reset_all_parser = subparsers.add_parser(
        "reset-all",
        help="Run west forall reset, pull mijo/manifest, then west update",
    )
    reset_all_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands only; do not execute",
    )
    reset_all_parser.set_defaults(func=cmd_reset_all)

    return parser


def main():
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
