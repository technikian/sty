"""
Install:
  pipenv install --dev
  pipenv run python make.py

Usage:
  make.py build wheel
  make.py build docs
  make.py deploy
  make.py test
  make.py bump
  make.py git
  make.py -h | --help

Options:
  -h, --help    Show this screen.
"""

import shutil
import os
import subprocess as sp
from cmdi import print_summary
from buildlib import git, wheel, project, yaml
from docopt import docopt
from sty import fg
import prmt

proj = yaml.loadfile('Project')


class Cfg:
    version = proj['version']
    registry = 'pypi'


def build_wheel(cfg: Cfg):
    return wheel.cmd.build(clean_dir=True)


def build_docs(cfg: Cfg):

    q = (
        f"{fg.red}WARNING{fg.rs}\n"
        "Documentation changes and code changes should use seperate commits.\n"
        "Only proceed if there are no uncommited code changes.\n\n"
        "Do you want to build the documentation pages?"
    )
    if not prmt.confirm(q, 'n'):
        return

    # Build Static Page with Sphinx
    sp.run(['make', 'html'], cwd='sphinx')

    build_html_dir = 'sphinx/_build/html'

    if os.path.isfile(f"{build_html_dir}/index.html"):
        shutil.rmtree('docs', ignore_errors=True)
        shutil.copytree(build_html_dir, 'docs')
        shutil.rmtree(build_html_dir, ignore_errors=True)
        shutil.copyfile('sphinx/CNAME', 'docs/CNAME')

    # Remove modernizer
    # This is needed to reduce flickering on page load until this is fixed:
    # https://github.com/readthedocs/sphinx_rtd_theme/issues/724
    from glob import glob

    for html_file in glob("./docs/**/*.html", recursive=True):
        print(html_file)
        data = ""
        with open(html_file, 'r') as fr:
            for line in fr:
                if 'modernizr.min.js"' not in line:
                    data += line

        with open(html_file, 'w') as fw:
            fw.write(data)


def deploy(cfg: Cfg):
    return wheel.cmd.push(clean_dir=True, repository=cfg.registry)


def test(cfg: Cfg):
    sp.run(['python', '-m', 'tests'])


def bump(cfg: Cfg):

    results = []

    if prmt.confirm("Do you want to BUMP VERSION number?", "n"):
        result = project.cmd.bump_version()
        cfg.version = result.val
        results.append(result)

    if prmt.confirm("Do you want to BUILD WHEEL?", "n"):
        results.append(build_wheel(cfg))

    if prmt.confirm("Do you want to PUSH WHEEL to PYPI?", "n"):
        results.append(deploy(cfg))

    if prmt.confirm("Do you want to BUILD DOCUMENTATION PAGES?", "n"):
        results.append(build_docs(cfg))

    new_release = cfg.version != proj['version']

    if prmt.confirm("Do you want to RUN GIT COMMANDS?", "n"):
        results.extend(git.seq.bump_git(cfg.version, new_release))

    return results


def run():

    cfg = Cfg()
    args = docopt(__doc__)
    results = []

    if args['build'] and args['wheel']:
        results.append(build_wheel(cfg))

    if args['build'] and args['docs']:
        results.append(build_docs(cfg))

    if args['deploy']:
        results.append(deploy(cfg))

    if args['test']:
        test(cfg)

    if args['git']:
        results.append(git.seq.bump_git(cfg.version, new_release=False))

    if args['bump']:
        results.extend(bump(cfg))

    if results:
        print_summary(results)


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        print('\n\nScript aborted by user.')
