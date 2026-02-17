Empanadas
================

Empanadas is the Rocky Linux Release Engineering toolkit for repeatable operations or functionality testing.

<center><img src='.github/empanadas.png' width=150px /></center>

Currently mirrored at our [github](https://github.com/rocky-linux), and the
[RESF Git Service](https://git.resf.org). Changes will typically occur at the
RESF Git Service.

What does this have?
--------------------

* analyze -> Analysis utilities (such as download stats)
* chat -> mattermost related utilities
* iso -> Contains `empanadas`, which provides legacy peridot ISO, Compose, and Sync related utilities.
* mangle -> Manglers, misc scripts that do not fit anywhere else
* sync -> Sync tools, used to sync from compose directories to mirror for Rocky Linux

How can I help?
---------------

Fork this repository and open a PR with your changes. Keep these things in mind
when you make changes:

* Your PR should be against the devel branch (not optional)
* Have pre-commit installed if possible
* Have shellcheck installed if possible
* Shell Scripts: These must pass a shellcheck test!
* Python scripts: Try your best to follow PEP8 guidelines (even the best linters get things wrong)

  * Note that not everything has to pass. Just try your best.

PR's against the main branch will be closed.

PR's are preferred at the [RESF Git Service](https://git.resf.org). PR's against
github will be closed.
