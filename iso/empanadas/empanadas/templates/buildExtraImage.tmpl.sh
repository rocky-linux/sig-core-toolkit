#!/bin/bash
set -ex

# funtions
function podman_setup_dirs() {
  {{ lorax_pkg_cmd }}
  mkdir -p {{ compose_work_iso_dir }}/{{ arch }}
  cd  {{ compose_work_iso_dir }}/{{ arch }}
  test -f {{ isoname }} && { echo "ERROR: ISO ALREDY EXISTS!"; exit 1; }
}

function podman_create_links() {
  # symlink to unversioned image name
  ln -sf {{ isoname }} {{ generic_isoname }}
  ln -sf {{ isoname }} {{ latest_isoname }}
  ln -sf {{ isoname }}.manifest {{ generic_isoname }}.manifest
  ln -sf {{ isoname }}.manifest {{ latest_isoname }}.manifest
}

function local_setup_env() {
  cd /builddir
  if ! TEMPLATE="$($(head -n1 $(which lorax) | cut -c3-) -c 'import pylorax; print(pylorax.find_templates())')"; then
    TEMPLATE="/usr/share/lorax"
  fi
}

function check_for_sorry() {
  if xorriso -indev {{ isoname }} -report_el_torito as_mkisofs 2>&1 | grep -q SORRY; then
    echo "IMAGE WAS NOT BUILT CORRECTLY"
    exit 23
  else
    return 0
  fi
}

{% if extra_iso_mode == "podman" %}
podman_setup_dirs
{% else %}
local_setup_env
{% endif %}

{{ make_image }}

{{ isohybrid }}

{{ implantmd5 }}

{{ make_manifest }}

## Check that the ISO came out fine
set +e
check_for_sorry
set -e

{% if extra_iso_mode == "podman" %}
podman_create_links
{% endif %}
