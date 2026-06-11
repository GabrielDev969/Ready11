#!/usr/bin/env python3
"""
Rename the Ready11 template into a new project. Run once right after cloning.

Usage:
    python scripts/bootstrap.py MyProject [--dry-run]

What it does:
    1. Replaces the template tokens in every git-tracked text file:
         Ready11            -> MyProject     (Django package, branding, docs)
         ready11            -> myproject     (package.json name, lockfile)
         ready_db           -> myproject_db  (database names, incl. CI variants)
         ready_redis        -> myproject_redis
         ready_mailpit      -> myproject_mailpit
         django_postgres_db -> myproject_postgres
    2. Renames the Django project package directory (git mv Ready11 MyProject).

Design notes:
    - Pure stdlib so it runs anywhere Python 3 exists (no sed -i BSD/GNU split).
    - Iterates over ``git ls-files`` only, so venv/, node_modules/ and other
      untracked artifacts are never touched. Binary files (e.g. compiled .mo
      translations) are skipped via UnicodeDecodeError.
    - Refuses to run on a dirty working tree so the rename lands as a single,
      reviewable (and revertable) commit.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

OLD_PASCAL = 'Ready11'
OLD_LOWER = 'ready11'
# Docker/database identifiers that embed the old project name.
OLD_TOKENS = ['ready_db', 'ready_redis', 'ready_mailpit']
OLD_POSTGRES_CONTAINER = 'django_postgres_db'


def git(*args, check=True):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=check)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('name', help='New project name (a valid Python identifier, e.g. MyProject)')
    parser.add_argument('--dry-run', action='store_true', help='Only list the files that would change')
    args = parser.parse_args()

    name = args.name
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', name):
        sys.exit('Error: name must start with a letter and contain only letters/digits (it becomes a Python package).')
    if name in (OLD_PASCAL, OLD_LOWER):
        sys.exit('Error: pick a name different from the template name.')
    slug = name.lower()

    repo_root = Path(git('rev-parse', '--show-toplevel').stdout.strip())
    if not args.dry_run and git('status', '--porcelain').stdout.strip():
        sys.exit('Error: working tree is not clean. Commit or stash your changes first.')

    changed = 0
    for rel in git('ls-files').stdout.splitlines():
        path = repo_root / rel
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, FileNotFoundError):
            continue  # binary file (.mo, images) or stale index entry

        new = text.replace(OLD_PASCAL, name).replace(OLD_LOWER, slug)
        for token in OLD_TOKENS:
            new = new.replace(token, token.replace('ready', slug, 1))
        new = new.replace(OLD_POSTGRES_CONTAINER, f'{slug}_postgres')

        if new != text:
            changed += 1
            print(f'  updating {rel}')
            if not args.dry_run:
                path.write_text(new, encoding='utf-8')

    if args.dry_run:
        print(f'\nDry run: {changed} file(s) would change, plus `git mv {OLD_PASCAL} {name}`.')
        return

    git('mv', OLD_PASCAL, name)
    print(f'\nRenamed {changed} file(s) and the {OLD_PASCAL}/ package directory.')
    print(f"""
Next steps:
  1. npm install                       # refresh package-lock.json with the new name
  2. cp .env.example .env              # then review PUBLIC_DOMAIN and secrets
  3. make setup && make docker-up && make migrate && make seed
  4. make messages && make compile     # refresh pt-BR translations for the new brand
  5. Review README.md branding/links, then commit:
       git add -A && git commit -m "chore: bootstrap {name} from Ready11 template"
  6. Delete scripts/bootstrap.py once you are happy with the result.
""")


if __name__ == '__main__':
    main()
