#!/bin/bash

VOLID="{{ shortname }}-{{ major }}-{{ minor }}{{ rc }}-{{ arch }}-boot1"
LOGFILE="{{ builddir }}/lorax-{{ arch }}.log"
VARIANT="{{ variant }}"
ARCH="{{ arch }}"
VERSION="{{ revision }}"
PRODUCT="{{ distname }}"
MOCKBLD="{{ builddir }}"
LORAXRES="{{ lorax_work_root }}"
LORAX_TAR="lorax-{{ major }}-{{ arch }}.tar.gz"

{% for pkg in lorax %}
sed -i '/{{ pkg }}/ s/^/#/' /usr/share/lorax/templates.d/80-rhel/runtime-install.tmpl
{% endfor %}

lorax --product="${PRODUCT}" \
  --version="${VERSION}" \
  --release="${VERSION}" \
{%- if rc == '' %}
  --isfinal \
{%- endif %}
{%- for repo in repos %}
  --source={{ repo.url }} \
{%- endfor %}
  --variant="${VARIANT}" \
  --nomacboot \
  --buildarch="${ARCH}" \
  --volid="${VOLID}" \
  --logfile="${LOGFILE}" \
  --rootfs-size=3 \
  "${LORAXRES}"

ret_val=$?
if [ $ret_val -ne 0 ]; then
  echo "!! LORAX FAILED !!"
  exit 1
fi

# If we didn't fail, let's pack up everything!
cd "${MOCKBLD}"
tar czf "${LORAX_TAR}" lorax "${LOGFILE}"

tar_ret_val=$?
if [ $ret_val -ne 0 ]; then
  echo "!! PROBLEM CREATING ARCHIVE !!"
  exit 1
fi

exit 0
