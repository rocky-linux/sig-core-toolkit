#!/bin/bash
set -ex

cd /builddir

if ! TEMPLATE="$($(head -n1 $(which lorax) | cut -c3-) -c 'import pylorax; print(pylorax.find_templates())')"; then
  TEMPLATE="/usr/share/lorax"
fi

{{ make_image }}

{{ isohybrid }}

{{ implantmd5 }}

{{ make_manifest }}
