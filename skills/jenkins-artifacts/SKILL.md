---
name: jenkins-artifacts
description: Use when downloading Jenkins build artifacts from the Jenkins SMB archive, especially Wear OS jobs like BuildWearOS7-BB2 with build numbers and glob filters such as '*.img' or '**/eMMC/'.
---

# Jenkins Artifacts

Use this skill to download Jenkins archived artifacts from the Jenkins SMB archive.

The helper script is in this skill directory:

```bash
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py
```

## Common Usage

Download the default artifact path for a job/build (`FLATBUILD/eMMC/`):

```bash
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py BuildWearOS7-BB2 19
```

Use another artifact subpath:

```bash
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py BuildWearOS7-BB2 19 --path FLATBUILD/eMMC/
```

Download only matching filenames:

```bash
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py BuildWearOS7-BB2 19 --filter '*.img'
```

Filters can also be positional:

```bash
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py BuildWearOS7-BB2 19 '*.img'
```

Preview matches without downloading:

```bash
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py BuildWearOS7-BB2 19 --dry-run --filter '*.img'
```

## Behavior

- Default SMB host: `192.168.1.114`
- Default SMB share: `Jenkins`
- Artifact root pattern: `jobs\\<job>\\builds\\<build>\\archive\\Artifact\\<build>`
- Default output: `download/<job>/<build>/`
- Default artifact subpath: `FLATBUILD/eMMC/`
- Downloads preserve artifact-relative paths.
- Completed files are marked with `.filename.ok` and skipped on rerun.
- Partial downloads use `.tmp` files and are atomically renamed when complete.

## Authentication

The script uses the same SMB host/share/user defaults as `/workspace/wear/pdk/script/_smb_download.py`. Provide the SMB password with an environment variable:

```bash
export JENKINS_SMB_USER='<username>'
export JENKINS_SMB_PASSWORD='<password>'
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py BuildWearOS7-BB2 19 --filter '*.img'
```

Or pass them explicitly:

```bash
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py BuildWearOS7-BB2 19 --user '<username>' --password '<token-or-password>'
```

## Options

```bash
~/.config/opencode/skills/jenkins-artifacts/download_jenkins_artifacts.py --help
```

Important flags:

- `--filter`, `-f`: Glob filter; repeatable.
- `--path`: Artifact subpath to list and download.
- `--out`, `-o`: Output directory.
- `--host`: SMB host override.
- `--share`: SMB share override.
- `--dry-run`: List matching files without downloading.
